from PIL import Image
import os
import numpy as np
import matplotlib.pyplot as plt

def clean_image(image_path, radius):
    """Extract circular region from center of image with given radius."""
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Get image dimensions
        height, width = img_array.shape[:2]
        
        # Find center point
        center_y = height // 2
        center_x = width // 2
        
        # Create a mask for the circle
        y, x = np.ogrid[:height, :width]
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        circle_mask = dist_from_center <= radius
        
        # Create output array with transparent background
        output = np.zeros_like(img_array)
        
        # Make output transparent by adding alpha channel if needed
        if output.shape[-1] == 3:  # RGB
            output = np.concatenate([output, np.zeros((*output.shape[:2], 1), dtype=output.dtype)], axis=-1)
        
        # Copy pixels inside circle mask
        if len(circle_mask.shape) == 2:
            circle_mask = np.stack([circle_mask] * output.shape[2], axis=2)
        output[circle_mask] = img_array[circle_mask]
        
        # Convert back to PIL Image with transparency
        circle_img = Image.fromarray(output, 'RGBA')
        
        # Crop to circle bounds
        box = (center_x - radius, center_y - radius, 
               center_x + radius, center_y + radius)
        cropped_circle = circle_img.crop(box)
        
        return cropped_circle
        
    except Exception as e:
        print(f"Error cleaning {image_path}: {str(e)}")
        return None

def find_and_display_test_image(directory_path):
    """Find first image with 'test' in the name and display it before and after cleaning."""
    # Supported image formats
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        print(f"Directory '{directory_path}' not found.")
        return
    
    # Find first test image
    test_image = None
    for filename in os.listdir(directory_path):
        if 'test' in filename.lower():
            file_ext = os.path.splitext(filename.lower())[1]
            if file_ext in supported_formats:
                test_image = os.path.join(directory_path, filename)
                break
    
    if test_image is None:
        print("No test image found.")
        return
    
    # Open and clean the image
    original = Image.open(test_image)
    cleaned = clean_image(test_image, 150)
    
    if cleaned is None:
        print("Error cleaning the image.")
        return
    
    # Display both images side by side
    plt.figure(figsize=(10, 5))
    
    plt.subplot(1, 2, 1)
    plt.imshow(original)
    plt.title('Original Image')
    plt.axis('off')
    
    plt.subplot(1, 2, 2)
    plt.imshow(cleaned)
    plt.title('Cleaned Image')
    plt.axis('off')
    
    plt.show()

def main():
    # Set the directory path
    images_directory = "images"
    
    print("Finding and displaying test image...")
    find_and_display_test_image(images_directory)

if __name__ == "__main__":
    main()
