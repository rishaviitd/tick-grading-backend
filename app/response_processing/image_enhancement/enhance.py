
#!/usr/bin/env python
import sys
import numpy as np
import matplotlib.pyplot as plt
import scipy.misc
import math
from PIL import Image
import random
import io
import os
from .utils import *
from .models import *

input_size = (256,256,1)

def enhance_image(image_bytes: bytes) -> bytes:
    """
    Enhance an image by applying deblur first, then binarization.
    
    Args:
        image_bytes: Input image as bytes
    
    Returns:
        Enhanced image as bytes (deblurred and binarized)
    
    Raises:
        Exception: If enhancement fails, returns original image bytes
    """
    try:
        # Get the directory of this file for loading weights
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Step 1: Load deblur model
        print("[enhance_image] Loading deblur model...")
        deblur_generator = generator_model(biggest_layer=1024)
        deblur_generator.load_weights(os.path.join(current_dir, "weights/deblur_weights.h5"))
        
        # Step 2: Load binarization model
        print("[enhance_image] Loading binarization model...")
        binarize_generator = generator_model(biggest_layer=1024)
        binarize_generator.load_weights(os.path.join(current_dir, "weights/binarization_generator_weights.h5"))
        
    except Exception as e:
        print(f"[enhance_image] Failed to load models: {e}")
        # Return original image if model loading fails
        return image_bytes
    
    try:
        # Convert bytes to PIL Image
        deg_image = Image.open(io.BytesIO(image_bytes))
        deg_image = deg_image.convert('L')
        
        # Save temporarily and read with matplotlib
        temp_path = 'temp_enhance_image.png'
        deg_image.save(temp_path)
        test_image = plt.imread(temp_path)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"[enhance_image] Failed to process image: {e}")
        # Return original image if processing fails
        return image_bytes
    
    try:
        # Process image for deblur
        print("[enhance_image] Applying deblur enhancement...")
        h = ((test_image.shape[0] // 256) + 1) * 256 
        w = ((test_image.shape[1] // 256) + 1) * 256
        
        test_padding = np.zeros((h, w)) + 1
        test_padding[:test_image.shape[0], :test_image.shape[1]] = test_image
        
        test_image_p = split2(test_padding.reshape(1, h, w, 1), 1, h, w)
        predicted_list = []
        
        for l in range(test_image_p.shape[0]):
            predicted_list.append(deblur_generator.predict(test_image_p[l].reshape(1, 256, 256, 1)))
        
        deblurred_image = np.array(predicted_list)
        deblurred_image = merge_image2(deblurred_image, h, w)
        
        deblurred_image = deblurred_image[:test_image.shape[0], :test_image.shape[1]]
        deblurred_image = deblurred_image.reshape(deblurred_image.shape[0], deblurred_image.shape[1])
        
        print("[enhance_image] Deblur completed, applying binarization...")
        
        # Now apply binarization to the deblurred image
        h = ((deblurred_image.shape[0] // 256) + 1) * 256 
        w = ((deblurred_image.shape[1] // 256) + 1) * 256
        
        test_padding = np.zeros((h, w)) + 1
        test_padding[:deblurred_image.shape[0], :deblurred_image.shape[1]] = deblurred_image
        
        test_image_p = split2(test_padding.reshape(1, h, w, 1), 1, h, w)
        predicted_list = []
        
        for l in range(test_image_p.shape[0]):
            predicted_list.append(binarize_generator.predict(test_image_p[l].reshape(1, 256, 256, 1)))
        
        predicted_image = np.array(predicted_list)
        predicted_image = merge_image2(predicted_image, h, w)
        
        predicted_image = predicted_image[:deblurred_image.shape[0], :deblurred_image.shape[1]]
        predicted_image = predicted_image.reshape(predicted_image.shape[0], predicted_image.shape[1])
        
        # Apply binarization threshold
        bin_thresh = 0.95
        predicted_image = (predicted_image[:, :] > bin_thresh) * 1
        
        # Convert back to bytes
        plt.imsave('temp_enhanced.png', predicted_image, cmap='gray')
        with open('temp_enhanced.png', 'rb') as f:
            enhanced_bytes = f.read()
        
        # Clean up temp file
        if os.path.exists('temp_enhanced.png'):
            os.remove('temp_enhanced.png')
        
        print("[enhance_image] Successfully applied deblur + binarization enhancement")
        return enhanced_bytes
        
    except Exception as e:
        print(f"[enhance_image] Failed to enhance image: {e}")
        # Return original image if enhancement fails
        return image_bytes

# Command line interface (existing functionality)
if __name__ == "__main__":
    # For command line usage, we need to use absolute imports
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from app.response_processing.image_enhancement.utils import *
    from app.response_processing.image_enhancement.models import *
    
    if len(sys.argv) != 3:
        print("Usage: python enhance.py <input_image_path> <output_image_path>")
        print("Applies deblur + binarization enhancement to the input image")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # Read input image
    with open(input_path, 'rb') as f:
        input_bytes = f.read()
    
    # Apply enhancement
    enhanced_bytes = enhance_image(input_bytes)
    
    # Save output
    with open(output_path, 'wb') as f:
        f.write(enhanced_bytes)
    
    print(f"Enhanced image saved to: {output_path}")



