import os
import logging
import numpy as np
from PIL import Image
import tensorflow as tf
from pathlib import Path

logger = logging.getLogger(__name__)

class MushroomClassifier:
    def __init__(self):
        """Initialize the MushroomClassifier with both edibility and species models."""
        try:
            # Get model paths
            base_path = Path('core/models/keras_models')
            edibility_model_path = base_path / 'edibility_model.keras'
            species_model_path = base_path / 'species_model.keras'
            
            logger.info(f"TensorFlow version: {tf.__version__}")
            logger.info(f"Keras version: {tf.keras.__version__}")
            
            # Define custom objects
            custom_objects = {
                'Functional': tf.keras.Model,
                'InputLayer': tf.keras.layers.InputLayer
            }
            
            # Load edibility model
            logger.info("\nLoading edibility model...")
            self.edibility_model = tf.keras.models.load_model(
                str(edibility_model_path),
                compile=False,
                custom_objects=custom_objects
            )
            logger.info("✓ Edibility model loaded successfully")
            
            # Load species model
            logger.info("\nLoading species model...")
            self.species_model = tf.keras.models.load_model(
                str(species_model_path),
                compile=False,
                custom_objects=custom_objects
            )
            logger.info("✓ Species model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise

    def preprocess_image(self, image_path, target_size=(224, 224)):
        """Preprocess the image for model input.
        
        Args:
            image_path: Path to the image file
            target_size: Target size for the image (default: 224x224)
            
        Returns:
            Preprocessed image array
        """
        try:
            # Load and resize image
            img = Image.open(image_path)
            img = img.resize(target_size)
            
            # Convert to array and preprocess
            img_array = np.array(img)
            img_array = img_array.astype('float32') / 255.0  # Normalize to [0,1]
            
            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise

    def analyze_image(self, image_path):
        """Analyze a mushroom image for edibility and species.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            dict: Analysis results including edibility and species predictions
        """
        try:
            # Preprocess image
            img_array = self.preprocess_image(image_path)
            
            # Get edibility prediction
            edibility_pred = self.edibility_model.predict(img_array, verbose=0)[0]
            is_edible = edibility_pred[1] > edibility_pred[0]
            edibility_score = float(edibility_pred[1] if is_edible else edibility_pred[0])
            
            # Get species predictions
            species_pred = self.species_model.predict(img_array, verbose=0)[0]
            
            # Get top-1 species prediction
            top_idx = int(np.argmax(species_pred))
            top_conf = float(species_pred[top_idx] * 100)
            
            # Example mapping: class index to preservation technique
            preservation_techniques = {
                0: "Refrigerate in a paper bag, use within 1 week.",
                1: "Drying or pickling recommended for longer storage.",
                2: "Store in a cool, dry place; avoid moisture.",
                3: "Best consumed fresh; refrigerate and use quickly.",
                4: "Can be frozen after blanching; also suitable for drying."
            }
            preservation = preservation_techniques.get(top_idx, "No data available.")
            
            species_prediction = {
                'class': top_idx,
                'confidence': top_conf,
                'preservation': preservation
            }
            
            return {
                'edibility': {
                    'is_edible': bool(is_edible),
                    'score': float(edibility_score * 100)  # Convert to percentage
                },
                'species': [species_prediction]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise 