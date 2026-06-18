from pharma_agent.domain.exceptions import (
    PhilosopherNameNotFound,
    PhilosopherPerspectiveNotFound,
    PhilosopherStyleNotFound,
)
from pharma_agent.domain.philosopher import Philosopher

PHILOSOPHER_NAMES = {
    "jnj": "Johnson & Johnson Assistant",
}

PHILOSOPHER_STYLES = {
    "jnj": "The J&J Assistant is helpful, professional, scientific, structured, and firmly guided by Our Credo.",
}

PHILOSOPHER_PERSPECTIVES = {
    "jnj": """The J&J Assistant acts as a knowledgeable corporate representative, detailing operations
across Innovative Medicine (oncology, immunology, neuroscience, cardiopulmonary) and MedTech (surgery,
orthopaedics, cardiovascular, vision), as well as J&J's history and core values (Our Credo).""",
}

PHILOSOPHER_ERAS = {
    "jnj": "Modern Era (1886 – Present). Dedicated to blending heart, science, and ingenuity to profoundly impact health for humanity.",
}

AVAILABLE_PHILOSOPHERS = list(PHILOSOPHER_STYLES.keys())


class PhilosopherFactory:
    @staticmethod
    def get_philosopher(id: str) -> Philosopher:
        """Creates a philosopher instance based on the provided ID.

        Args:
            id (str): Identifier of the philosopher to create

        Returns:
            Philosopher: Instance of the philosopher

        Raises:
            ValueError: If philosopher ID is not found in configurations
        """
        id_lower = id.lower()

        if id_lower not in PHILOSOPHER_NAMES:
            raise PhilosopherNameNotFound(id_lower)

        if id_lower not in PHILOSOPHER_PERSPECTIVES:
            raise PhilosopherPerspectiveNotFound(id_lower)

        if id_lower not in PHILOSOPHER_STYLES:
            raise PhilosopherStyleNotFound(id_lower)

        return Philosopher(
            id=id_lower,
            name=PHILOSOPHER_NAMES[id_lower],
            perspective=PHILOSOPHER_PERSPECTIVES[id_lower],
            style=PHILOSOPHER_STYLES[id_lower],
            era=PHILOSOPHER_ERAS[id_lower],
        )

    @staticmethod
    def get_available_philosophers() -> list[str]:
        """Returns a list of all available philosopher IDs.

        Returns:
            list[str]: List of philosopher IDs that can be instantiated
        """
        return AVAILABLE_PHILOSOPHERS
