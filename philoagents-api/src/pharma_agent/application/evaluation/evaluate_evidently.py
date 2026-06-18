import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from loguru import logger
from evidently import Dataset, Report
from evidently.presets import TextEvals
from evidently.descriptors import (
    TextLength,
    Sentiment,
    SemanticSimilarity,
    CorrectnessLLMEval,
    FaithfulnessLLMEval,
    ContextQualityLLMEval,
    ToxicityLLMEval,
)

from pharma_agent.application.conversation_service.generate_response import get_response
from pharma_agent.application.conversation_service.workflow.state import state_to_str
from pharma_agent.config import settings
from pharma_agent.domain.philosopher_factory import PhilosopherFactory


async def run_single_sample(
    sample: Dict[str, Any], semaphore: asyncio.Semaphore, philosopher_factory: PhilosopherFactory
) -> Dict[str, Any] | None:
    """Runs the LangGraph agent for a single evaluation dataset sample."""
    async with semaphore:
        try:
            philosopher_id = sample["philosopher_id"]
            philosopher = philosopher_factory.get_philosopher(philosopher_id)
            
            messages = sample["messages"]
            if not messages:
                return None
                
            input_messages = messages[:-1]
            expected_output_message = messages[-1]
            
            user_query = input_messages[-1]["content"] if input_messages else ""
            expected_response = expected_output_message.get("content", "")
            
            logger.info(f"Running agent for philosopher '{philosopher_id}' on query: '{user_query[:40]}...'")
            
            response, latest_state = await get_response(
                messages=input_messages,
                philosopher_id=philosopher.id,
                philosopher_name=philosopher.name,
                philosopher_perspective=philosopher.perspective,
                philosopher_style=philosopher.style,
                philosopher_era=philosopher.era,
                philosopher_context="",
                new_thread=True,
            )
            
            context = state_to_str(latest_state)
            
            return {
                "philosopher_id": philosopher_id,
                "user_query": user_query,
                "context": context,
                "generated_response": response,
                "expected_response": expected_response,
            }
        except Exception as e:
            logger.error(f"Error processing sample: {e}")
            return None


async def run_evaluation_pipeline(
    data_path: Path, nb_samples: int | None = None, workers: int = 2
) -> pd.DataFrame:
    """Executes the agent workflow over the dataset and returns a pandas DataFrame of results."""
    logger.info(f"Loading evaluation dataset from {data_path}")
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    samples = data.get("samples", [])
    if nb_samples is not None:
        samples = samples[:nb_samples]
        
    logger.info(f"Found {len(samples)} samples to evaluate.")
    
    philosopher_factory = PhilosopherFactory()
    semaphore = asyncio.Semaphore(workers)
    
    tasks = [run_single_sample(sample, semaphore, philosopher_factory) for sample in samples]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed samples
    valid_results = [r for r in results if r is not None]
    logger.info(f"Successfully processed {len(valid_results)}/{len(samples)} samples.")
    
    return pd.DataFrame(valid_results)


def evaluate_agent_evidently(
    data_path: Path,
    nb_samples: int | None = None,
    workers: int = 2,
    output_html_path: str = "evidently_report.html",
    output_json_path: str = "evidently_report.json",
) -> None:
    """Runs evaluation using Evidently AI metrics on agent outputs."""
    df = asyncio.run(run_evaluation_pipeline(data_path, nb_samples, workers))
    
    if df.empty:
        logger.error("No successful evaluation results. Evidently report will not be generated.")
        return
        
    logger.info("Initializing Evidently evaluation report...")
    
    # 1. Create Evidently Dataset
    dataset = Dataset.from_pandas(df)
    
    # 2. Configure text quality descriptors
    descriptors = [
        TextLength(column_name="generated_response", alias="Response Character Length"),
        Sentiment(column_name="generated_response", alias="Response Sentiment"),
        SemanticSimilarity(
            columns=["generated_response", "expected_response"],
            alias="Semantic Similarity to Expected"
        )
    ]
    
    # Include LLM-as-a-judge if OpenAI key is configured
    if settings.OPENAI_API_KEY:
        if "OPENAI_API_KEY" not in os.environ:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
            
        try:
            logger.info("Adding LLM-as-a-judge metrics...")
            descriptors.append(
                CorrectnessLLMEval(
                    column_name="generated_response",
                    target_output="expected_response",
                    provider="openai",
                    model="gpt-4o-mini",
                    alias="Correctness",
                )
            )
            descriptors.append(
                FaithfulnessLLMEval(
                    column_name="generated_response",
                    context="context",
                    provider="openai",
                    model="gpt-4o-mini",
                    alias="Faithfulness",
                )
            )
            descriptors.append(
                ContextQualityLLMEval(
                    column_name="context",
                    question="user_query",
                    provider="openai",
                    model="gpt-4o-mini",
                    alias="Context Quality",
                )
            )
            descriptors.append(
                ToxicityLLMEval(
                    column_name="generated_response",
                    provider="openai",
                    model="gpt-4o-mini",
                    alias="Response Toxicity",
                )
            )
        except Exception as e:
            logger.warning(f"Could not initialize Evidently LLM-as-a-judge descriptors: {e}. Skipping them.")
            
    logger.info("Adding descriptors to dataset...")
    dataset.add_descriptors(descriptors)
    
    # 3. Create Report with TextEvals preset
    report = Report(metrics=[TextEvals()])
    
    logger.info("Running Evidently metrics...")
    snap = report.run(reference_data=None, current_data=dataset)
    
    # 4. Save reports from snapshot
    snap.save_html(output_html_path)
    snap.save_json(output_json_path)
    logger.info(f"Evidently HTML report saved to: {output_html_path}")
    logger.info(f"Evidently JSON report saved to: {output_json_path}")

    # 5. Log to local Evidently UI workspace database
    try:
        from evidently.ui.workspace import Workspace
        ws = Workspace.create("workspace")
        project = None
        for p in ws.list_projects():
            if p.name == "Philosopher Agents Evaluation":
                project = p
                break
        if project is None:
            project = ws.create_project("Philosopher Agents Evaluation")
            project.description = "Offline evaluation metrics for pharma_agent."
            try:
                from evidently.sdk.panels import PanelMetric, line_plot_panel, counter_panel
                
                # Tab 1: Overview
                project.dashboard.add_panel(
                    counter_panel(
                        title="Total Evaluation Samples",
                        values=[PanelMetric(metric="RowCount", legend="Samples")],
                        aggregation="sum",
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    counter_panel(
                        title="Mean Semantic Similarity",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Semantic Similarity to Expected"}, legend="Similarity Score")],
                        aggregation="last",
                        size="half"
                    )
                )
                
                # Tab 2: Response Quality
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Mean Response Length Over Time",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Response Character Length"}, legend="Length (Chars)")],
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Mean Response Sentiment Over Time",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Response Sentiment"}, legend="Sentiment Score")],
                        size="half"
                    )
                )

                # Tab 3: RAG & LLM-as-a-judge
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Answer Correctness & Faithfulness",
                        values=[
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Correctness"}, legend="Correctness"),
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Faithfulness"}, legend="Faithfulness")
                        ],
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Retrieval Context Quality",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Context Quality"}, legend="Context Quality")],
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Response Toxicity Rating",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Response Toxicity"}, legend="Toxicity Score")],
                        size="full"
                    )
                )
                project.save()
            except Exception as pe:
                logger.warning(f"Could not initialize dashboard panels: {pe}")
        
        ws.add_run(project.id, snap)
        logger.info("Evaluation snapshot successfully logged to local Evidently UI workspace database.")
    except Exception as e:
        logger.warning(f"Could not log snapshot to Evidently UI workspace: {e}")


def log_chat_interaction_to_evidently(
    user_query: str,
    generated_response: str,
    philosopher_id: str,
    context: str = ""
) -> None:
    """Logs a single real-time user-agent interaction to the Evidently UI workspace database."""
    logger.info(f"Logging real-time interaction to Evidently: philosopher={philosopher_id}")

    df = pd.DataFrame([{
        "philosopher_id": philosopher_id,
        "user_query": user_query,
        "generated_response": generated_response,
        "expected_response": "",  # No reference answer for live chat
        "context": context
    }])

    # 1. Create Evidently Dataset
    dataset = Dataset.from_pandas(df)

    # 2. Configure text quality descriptors (no semantic similarity as there's no reference target)
    descriptors = [
        TextLength(column_name="generated_response", alias="Response Character Length"),
        Sentiment(column_name="generated_response", alias="Response Sentiment"),
        TextLength(column_name="user_query", alias="Query Character Length"),
        Sentiment(column_name="user_query", alias="Query Sentiment")
    ]

    # Include LLM-as-a-judge if OpenAI key is configured
    if settings.OPENAI_API_KEY:
        if "OPENAI_API_KEY" not in os.environ:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        try:
            descriptors.append(
                ToxicityLLMEval(
                    column_name="generated_response",
                    provider="openai",
                    model="gpt-4o-mini",
                    alias="Response Toxicity"
                )
            )
            descriptors.append(
                ToxicityLLMEval(
                    column_name="user_query",
                    provider="openai",
                    model="gpt-4o-mini",
                    alias="Query Toxicity"
                )
            )
            if context:
                descriptors.append(
                    FaithfulnessLLMEval(
                        column_name="generated_response",
                        context="context",
                        provider="openai",
                        model="gpt-4o-mini",
                        alias="Response Faithfulness"
                    )
                )
                descriptors.append(
                    ContextQualityLLMEval(
                        column_name="context",
                        question="user_query",
                        provider="openai",
                        model="gpt-4o-mini",
                        alias="Context Quality"
                    )
                )
        except Exception as e:
            logger.warning(f"Could not initialize Evidently LLM descriptors for live monitoring: {e}")

    dataset.add_descriptors(descriptors)

    # 3. Create Report with TextEvals preset
    report = Report(metrics=[TextEvals()])
    snap = report.run(reference_data=None, current_data=dataset)

    # 4. Log to local Evidently UI workspace database under "Philosopher Agents Live Monitoring"
    try:
        from evidently.ui.workspace import Workspace
        ws = Workspace.create("workspace")
        project = None
        for p in ws.list_projects():
            if p.name == "Philosopher Agents Live Monitoring":
                project = p
                break
        if project is None:
            project = ws.create_project("Philosopher Agents Live Monitoring")
            project.description = "Real-time production monitoring of philosopher chat logs."
            try:
                from evidently.sdk.panels import PanelMetric, line_plot_panel, counter_panel
                
                # Tab 1: Overview
                project.dashboard.add_panel(
                    counter_panel(
                        title="Total Logged Interactions",
                        values=[PanelMetric(metric="RowCount", legend="Chats")],
                        aggregation="sum",
                        size="full"
                    )
                )
                
                # Tab 2: Conversations
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="User Query Length vs Agent Response Length",
                        values=[
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Query Character Length"}, legend="User Query Chars"),
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Response Character Length"}, legend="Agent Response Chars")
                        ],
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="User Sentiment vs Agent Sentiment",
                        values=[
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Query Sentiment"}, legend="User Sentiment"),
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Response Sentiment"}, legend="Agent Sentiment")
                        ],
                        size="half"
                    )
                )

                # Tab 3: RAG & Moderation
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Agent Response Faithfulness",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Response Faithfulness"}, legend="Faithfulness Score")],
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Retrieval Context Quality",
                        values=[PanelMetric(metric="MeanValue", metric_labels={"column": "Context Quality"}, legend="Context Quality")],
                        size="half"
                    )
                )
                project.dashboard.add_panel(
                    line_plot_panel(
                        title="Toxicity Ratings",
                        values=[
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Query Toxicity"}, legend="User Query Toxicity"),
                            PanelMetric(metric="MeanValue", metric_labels={"column": "Response Toxicity"}, legend="Agent Response Toxicity")
                        ],
                        size="half"
                    )
                )
                project.save()
            except Exception as pe:
                logger.warning(f"Could not initialize live dashboard panels: {pe}")
 
        ws.add_run(project.id, snap)
        logger.info("Real-time interaction snapshot successfully logged to local Evidently UI workspace.")
    except Exception as e:
        logger.warning(f"Could not log real-time snapshot to Evidently UI workspace: {e}")
