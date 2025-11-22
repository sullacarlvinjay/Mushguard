import tensorflow as tf
import logging
from pathlib import Path
import numpy as np
from PIL import Image
import os
from typing import Dict, Any, Optional
from functools import lru_cache

# Suppress all TensorFlow logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TF logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)

# Configure root logger with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TFLiteModel:
    """Wrapper class for TFLite model inference."""
    def __init__(self, model_path: str):
        self.interpreter = tf.lite.Interpreter(model_path=str(model_path))
        self.interpreter.allocate_tensors()
        
        # Get input and output details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Get input shape
        self.input_shape = tuple(self.input_details[0]['shape'][1:3])  # Height, Width
        
        # Log detailed model information
        logger.info(f"\n{'='*50}")
        logger.info(f"Model loaded from: {model_path}")
        logger.info(f"Model type: TFLite")
        logger.info(f"\nInput Details:")
        logger.info(f"- Shape: {self.input_details[0]['shape']}")
        logger.info(f"- Type: {self.input_details[0]['dtype']}")
        logger.info(f"- Name: {self.input_details[0]['name']}")
        logger.info(f"\nOutput Details:")
        logger.info(f"- Shape: {self.output_details[0]['shape']}")
        logger.info(f"- Type: {self.output_details[0]['dtype']}")
        logger.info(f"- Name: {self.output_details[0]['name']}")
        logger.info(f"{'='*50}\n")

    def predict(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference on the model."""
        input_detail = self.input_details[0]
        tensor = input_data

        # Handle quantized inputs by transforming float data to the expected dtype
        scale, zero_point = input_detail.get('quantization', (0.0, 0))
        if scale and scale != 0.0:
            tensor = np.round(tensor / scale + zero_point)
            if np.issubdtype(input_detail['dtype'], np.integer):
                info = np.iinfo(input_detail['dtype'])
                tensor = np.clip(tensor, info.min, info.max)
            tensor = tensor.astype(input_detail['dtype'])
        else:
            tensor = tensor.astype(input_detail['dtype'])

        # Set input tensor
        self.interpreter.set_tensor(input_detail['index'], tensor)
        
        # Run inference
        self.interpreter.invoke()
        
        # Get output tensor and dequantize if needed
        output_detail = self.output_details[0]
        output_data = self.interpreter.get_tensor(output_detail['index'])
        out_scale, out_zero_point = output_detail.get('quantization', (0.0, 0))
        if out_scale and out_scale != 0.0:
            output_data = out_scale * (output_data.astype(np.float32) - out_zero_point)
        return output_data

# Model paths
MODEL_BASE_PATH = Path(__file__).parent / 'models' / 'keras_models'
MUSHROOM_MODEL_PATH = MODEL_BASE_PATH / 'mush.tflite'
EDIBILITY_MODEL_PATH = MODEL_BASE_PATH / 'edibility_model.tflite'
SPECIES_MODEL_PATH = MODEL_BASE_PATH / 'species_model.tflite'

# Verify model files exist
if not MUSHROOM_MODEL_PATH.exists():
    raise FileNotFoundError(f"Mushroom detector model not found at {MUSHROOM_MODEL_PATH}")
if not EDIBILITY_MODEL_PATH.exists():
    raise FileNotFoundError(f"Edibility model not found at {EDIBILITY_MODEL_PATH}")
if not SPECIES_MODEL_PATH.exists():
    raise FileNotFoundError(f"Species model not found at {SPECIES_MODEL_PATH}")

# Species information
SPECIES_INFO = {
    'Apioperdon_pyriforme': {
        'lifespan': 'Room temp. 12hours after harvest. The mushroom is edible when its interior is completely white. Once the spores inside become yellow or the interior turns tan to brown, the mushroom should not be eaten.',
        'preservation': 'refrigerated 3-5 days.'
    },
    'Cerioporus_squamosus': {
        'lifespan': '4hours room temp after harvest',
        'preservation': '1 week refrigerated. Pheasant back mushrooms can be frozen. It is generally recommended to cook them first, such as by steaming or sautéing, as this helps maintain a better texture upon thawing.'
    },
    'Coprinellus_micaceus': {
        'lifespan': '1-2 days room temp after harvest',
        'preservation': 'refrigerated 3-5 days.'
    },
    'Coprinus_comatus': {
        'lifespan': '24 hours (dissolves quickly)',
        'preservation': 'less than 3 days room temp after harvest; 10 days refrigerated, 18 days with treatment; 2 years properly sealed and dried.'
    },
    'lactarius_torminosus': {
        'lifespan': '1-2 days room temp after harvest',
        'preservation': 'refrigerated 3-7 days.'
    }
}

@lru_cache(maxsize=1)
def get_mushroom_detector_model() -> TFLiteModel:
    """Get the mushroom/not-mushroom detector model (mush.tflite)."""
    try:
        logger.info("Loading mushroom detector model (mush.tflite)...")
        return TFLiteModel(MUSHROOM_MODEL_PATH)
    except Exception as e:
        logger.error(f"Error loading mushroom detector model: {str(e)}")
        raise

@lru_cache(maxsize=2)
def get_edibility_model() -> TFLiteModel:
    """Get the edibility model."""
    try:
        logger.info("Loading edibility model...")
        return TFLiteModel(EDIBILITY_MODEL_PATH)
    except Exception as e:
        logger.error(f"Error loading edibility model: {str(e)}")
        raise

@lru_cache(maxsize=1)
def get_species_model() -> TFLiteModel:
    """Get the species model."""
    try:
        logger.info("Loading species model...")
        return TFLiteModel(SPECIES_MODEL_PATH)
    except Exception as e:
        logger.error(f"Error loading species model: {str(e)}")
        raise

def preprocess_mushroom_image(image: Image.Image) -> np.ndarray:
    """Preprocess the image for mushroom detector model input (mush.tflite)."""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        model = get_mushroom_detector_model()
        logger.info(f"Resizing image to mushroom detector input shape: {model.input_shape}")
        img = image.resize(model.input_shape)
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        logger.info(f"Preprocessed mushroom-detector image shape: {img_array.shape}")
        return img_array
    except Exception as e:
        logger.error(f"Error preprocessing mushroom-detector image: {str(e)}")
        raise

def preprocess_edibility_image(image: Image.Image) -> np.ndarray:
    """Preprocess the image for edibility model input."""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        # Get the model's expected input shape
        model = get_edibility_model()
        logger.info(f"Resizing image to edibility model input shape: {model.input_shape}")
        img = image.resize(model.input_shape)
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        logger.info(f"Preprocessed image shape: {img_array.shape}")
        return img_array
    except Exception as e:
        logger.error(f"Error preprocessing edibility image: {str(e)}")
        raise

def preprocess_species_image(image: Image.Image) -> np.ndarray:
    """Preprocess the image for species model input."""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        # Get the model's expected input shape
        model = get_species_model()
        logger.info(f"Resizing image to species model input shape: {model.input_shape}")
        img = image.resize(model.input_shape)
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        logger.info(f"Preprocessed image shape: {img_array.shape}")
        return img_array
    except Exception as e:
        logger.error(f"Error preprocessing species image: {str(e)}")
        raise

def preliminary_check(image: Image.Image) -> Dict[str, Any]:
    """Preliminary check using mush.tflite to determine if the image is a mushroom.

    Uses the mushroom detector model as an authentication step before running the
    main edibility/species analysis. If the mushroom probability is below 95%,
    the image is treated as not a mushroom and further analysis is skipped.
    """
    try:
        logger.info("Starting preliminary mushroom authentication using mush.tflite...")

        # Use mushroom detector model for preliminary identification
        mush_input = preprocess_mushroom_image(image)
        mush_model = get_mushroom_detector_model()
        mush_pred = mush_model.predict(mush_input)

        # Interpret prediction as mushroom probability
        # If the model outputs a single probability, use that; otherwise use max class prob
        raw_output = mush_pred[0]
        if raw_output.shape[0] == 1:
            # Single-output models usually represent the probability of the negative class
            # ("not a mushroom"). Convert it to a mushroom confidence by inverting.
            not_mushroom_prob = float(raw_output[0]) * 100.0
            mushroom_prob = 100.0 - not_mushroom_prob
        else:
            mushroom_prob = float(np.max(raw_output)) * 100.0

        logger.info(f"Mushroom detector probability: {mushroom_prob}%")

        # Reject anything below the 60% mushroom confidence threshold
        if mushroom_prob < 60.0:
            return {
                'preliminary_passed': False,
                'confidence': mushroom_prob,
                'message': 'Image is not a mushroom. Please upload another image.'
            }
        else:
            return {
                'preliminary_passed': True,
                'confidence': mushroom_prob
            }
        
    except Exception as e:
        logger.error(f"Error in preliminary check: {str(e)}")
        return {'error': str(e)}

def analyze_mushroom(image: Image.Image) -> Dict[str, Any]:
    """Analyze a mushroom image for edibility and species."""
    try:
        logger.info("Starting mushroom analysis...")
        
        # First run preliminary check
        preliminary_result = preliminary_check(image)
        if 'error' in preliminary_result:
            return preliminary_result
        
        # If preliminary check fails, return early
        if not preliminary_result['preliminary_passed']:
            return preliminary_result
        
        logger.info("Preliminary check passed, proceeding with detailed analysis...")
        
        # First analyze edibility
        logger.info("Analyzing edibility...")
        edibility_input = preprocess_edibility_image(image)
        edibility_model = get_edibility_model()
        edibility_pred = edibility_model.predict(edibility_input)
        
        # Get edibility prediction and confidence
        edible_prob = float(edibility_pred[0][0])
        is_edible = edible_prob > 0.5
        confidence = float(abs(edible_prob - 0.5) * 2) * 100  # Convert to percentage
        
        result = {
            'is_edible': is_edible,
            'edibility_confidence': confidence,
            'edibility_probability': edible_prob
        }
        
        # If edible, proceed with species identification
        if is_edible:
            logger.info("Mushroom is edible, analyzing species...")
            species_input = preprocess_species_image(image)
            species_model = get_species_model()
            species_pred = species_model.predict(species_input)
            
            # Get top prediction
            species_idx = np.argmax(species_pred[0])
            species_confidence = float(species_pred[0][species_idx]) * 100
            
            species_labels = [
                'Apioperdon_pyriforme',
                'Cerioporus_squamosus',
                'Coprinellus_micaceus',
                'Coprinus_comatus',
                'lactarius_torminosus'
            ]
            
            species = species_labels[species_idx]
            info = SPECIES_INFO.get(species, {})
            
            result.update({
                'species': species,
                'species_confidence': species_confidence,
                'species_probability': float(species_pred[0][species_idx]),
                'lifespan': info.get('lifespan', 'Unknown'),
                'preservation': info.get('preservation', 'Unknown')
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in mushroom analysis: {str(e)}")
        return {'error': str(e)}