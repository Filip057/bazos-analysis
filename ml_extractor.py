"""
Machine Learning-based Car Data Extractor using spaCy NER
==========================================================

This module uses Named Entity Recognition (NER) to extract structured data
from Czech car listings. It's designed for learning ML basics while solving
a real problem.

Concepts covered:
- Named Entity Recognition (NER)
- Training data preparation
- Model training
- Prediction and evaluation
"""

import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
import random
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class CarDataExtractor:
    """
    ML-based extractor for car information from Czech text.

    This uses spaCy's NER (Named Entity Recognition) to identify:
    - MILEAGE: kilometers driven
    - YEAR: year of manufacture
    - POWER: engine power in kW
    - FUEL: fuel type
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            model_path: Path to trained model. If None, creates blank model.
        """
        self.model_path = model_path
        self.nlp = None

        if model_path and Path(model_path).exists():
            logger.info(f"Loading trained model from {model_path}")
            self.nlp = spacy.load(model_path)
        else:
            logger.info("Creating blank Czech model")
            self.nlp = spacy.blank("cs")  # Czech language

    def train(self, training_data: List[Tuple[str, Dict]],
              n_iter: int = 30,
              output_dir: str = "./car_ner_model"):
        """
        Train the NER model on labeled data.

        Args:
            training_data: List of (text, annotations) tuples
            n_iter: Number of training iterations
            output_dir: Where to save the trained model

        Example training_data format:
            [
                ("Škoda Octavia 2015, 120000 km, 110 kW", {
                    "entities": [(18, 26, "MILEAGE"), (14, 18, "YEAR"), (28, 34, "POWER")]
                }),
                ...
            ]
        """
        logger.info(f"Starting training with {len(training_data)} examples...")

        # Add NER pipeline component if not exists
        if "ner" not in self.nlp.pipe_names:
            ner = self.nlp.add_pipe("ner")
        else:
            ner = self.nlp.get_pipe("ner")

        # Add labels (the entity types we want to recognize)
        for _, annotations in training_data:
            for ent in annotations.get("entities", []):
                ner.add_label(ent[2])  # Add label (MILEAGE, YEAR, etc.)

        # Disable other pipelines during training
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
        with self.nlp.disable_pipes(*other_pipes):

            # Initialize the model
            optimizer = self.nlp.begin_training()

            # Training loop
            for iteration in range(n_iter):
                random.shuffle(training_data)
                losses = {}

                # Batch training for efficiency
                batches = minibatch(training_data, size=compounding(4.0, 32.0, 1.001))

                for batch in batches:
                    examples = []
                    for text, annotations in batch:
                        doc = self.nlp.make_doc(text)
                        example = Example.from_dict(doc, annotations)
                        examples.append(example)

                    # Update the model
                    self.nlp.update(
                        examples,
                        drop=0.5,  # Dropout for regularization
                        losses=losses,
                        sgd=optimizer
                    )

                # Log progress every 5 iterations
                if (iteration + 1) % 5 == 0:
                    logger.info(f"Iteration {iteration + 1}/{n_iter}, Loss: {losses.get('ner', 0):.2f}")

        # Save the trained model
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        self.nlp.to_disk(output_path)
        logger.info(f"✓ Model saved to {output_dir}")

        # Save metadata
        with open(output_path / "metadata.json", "w") as f:
            json.dump({
                "n_iter": n_iter,
                "n_examples": len(training_data),
                "labels": list(ner.labels)
            }, f, indent=2)

    def extract(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract car information from text using the trained model.

        Args:
            text: Car listing description

        Returns:
            Dictionary with extracted values: {mileage, year, power, fuel}
        """
        if not self.nlp:
            raise ValueError("Model not loaded. Train or load a model first.")

        doc = self.nlp(text)

        result = {
            'mileage': None,
            'year': None,
            'power': None,
            'fuel': None
        }

        # Extract entities found by the model
        for ent in doc.ents:
            if ent.label_ == "MILEAGE":
                result['mileage'] = self._parse_mileage(ent.text)
            elif ent.label_ == "YEAR":
                result['year'] = self._parse_year(ent.text)
            elif ent.label_ == "POWER":
                result['power'] = self._parse_power(ent.text)
            elif ent.label_ == "FUEL":
                result['fuel'] = ent.text.lower()

        logger.debug(f"Extracted from '{text[:50]}...': {result}")
        return result

    def _parse_mileage(self, text: str) -> Optional[int]:
        """Convert mileage text to integer"""
        # Extract numbers and handle "tis" (thousands)
        text = text.lower().replace(' ', '')

        if 'tis' in text:
            match = re.search(r'(\d+)', text)
            if match:
                return int(match.group(1)) * 1000

        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None

    def _parse_year(self, text: str) -> Optional[int]:
        """Convert year text to integer"""
        match = re.search(r'(\d{4})', text)
        if match:
            year = int(match.group(1))
            # Validate year range
            if 1900 <= year <= 2030:
                return year
        return None

    def _parse_power(self, text: str) -> Optional[int]:
        """Convert power text to integer"""
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None

    def evaluate(self, test_data: List[Tuple[str, Dict]]) -> Dict:
        """
        Evaluate model performance on test data.

        Args:
            test_data: List of (text, expected_annotations) tuples

        Returns:
            Dictionary with precision, recall, F1 scores
        """
        if not self.nlp:
            raise ValueError("Model not loaded")

        examples = []
        for text, annotations in test_data:
            doc = self.nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)

        # Get scores from spaCy
        scores = self.nlp.evaluate(examples)

        logger.info(f"Evaluation results: Precision={scores['ents_p']:.2f}, "
                   f"Recall={scores['ents_r']:.2f}, F1={scores['ents_f']:.2f}")

        return {
            'precision': scores['ents_p'],
            'recall': scores['ents_r'],
            'f1': scores['ents_f']
        }


def create_training_data_from_csv(csv_path: str) -> List[Tuple[str, Dict]]:
    """
    Helper function to convert labeled CSV data to spaCy training format.

    CSV format:
    text,mileage_start,mileage_end,year_start,year_end,power_start,power_end
    "Škoda 2015 120000km 110kW",12,20,6,10,21,27

    Returns:
        Training data in spaCy format
    """
    import csv

    training_data = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row['text']
            entities = []

            # Add mileage entity if present
            if row.get('mileage_start') and row.get('mileage_end'):
                entities.append((
                    int(row['mileage_start']),
                    int(row['mileage_end']),
                    "MILEAGE"
                ))

            # Add year entity if present
            if row.get('year_start') and row.get('year_end'):
                entities.append((
                    int(row['year_start']),
                    int(row['year_end']),
                    "YEAR"
                ))

            # Add power entity if present
            if row.get('power_start') and row.get('power_end'):
                entities.append((
                    int(row['power_start']),
                    int(row['power_end']),
                    "POWER"
                ))

            training_data.append((text, {"entities": entities}))

    return training_data


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create small example training dataset
    TRAINING_DATA = [
        ("Škoda Octavia 2015, najeto 120000 km, výkon 110 kW", {
            "entities": [(28, 38, "MILEAGE"), (14, 18, "YEAR"), (46, 52, "POWER")]
        }),
        ("BMW 2018, 85 tis km, 150kW, benzín", {
            "entities": [(10, 18, "MILEAGE"), (4, 8, "YEAR"), (20, 25, "POWER")]
        }),
        ("Rok výroby 2020, najeté 50000 km, 100 kW", {
            "entities": [(11, 15, "YEAR"), (24, 32, "MILEAGE"), (34, 40, "POWER")]
        }),
        # Add more examples here...
    ]

    # Initialize and train
    extractor = CarDataExtractor()
    extractor.train(TRAINING_DATA, n_iter=20, output_dir="./ml_models/car_ner")

    # Test extraction
    test_texts = [
        "Prodám Volkswagen Golf rok 2016, najeto 95000 km, motor 105 kW",
        "Škoda Fabia 2019, 45 tis km, 70kW"
    ]

    for text in test_texts:
        result = extractor.extract(text)
        print(f"\nText: {text}")
        print(f"Extracted: {result}")
