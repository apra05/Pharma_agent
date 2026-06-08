from pathlib import Path

import click

from philoagents.application.evaluation import evaluate_agent_evidently
from philoagents.config import settings


@click.command()
@click.option(
    "--data-path",
    type=click.Path(exists=True, path_type=Path),
    default=settings.EVALUATION_DATASET_FILE_PATH,
    help="Path to the dataset file",
)
@click.option("--workers", default=2, type=int, help="Number of parallel workers")
@click.option(
    "--nb-samples", default=20, type=int, help="Number of samples to evaluate"
)
@click.option(
    "--output-html", default="evidently_report.html", help="Path to output HTML report"
)
@click.option(
    "--output-json", default="evidently_report.json", help="Path to output JSON report"
)
def main(data_path: Path, workers: int, nb_samples: int, output_html: str, output_json: str) -> None:
    """
    Evaluate the agent on a dataset using Evidently AI.
    """
    evaluate_agent_evidently(
        data_path=data_path,
        nb_samples=nb_samples,
        workers=workers,
        output_html_path=output_html,
        output_json_path=output_json,
    )


if __name__ == "__main__":
    main()
