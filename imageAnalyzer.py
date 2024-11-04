from PIL import Image
import os
import numpy as np

def clean_image(image_path):
    """Remove black background and crop to the circle."""
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Find non-black pixels (assuming pure black is [0,0,0])
        # Using a small threshold to account for possible compression artifacts
        threshold = 5
        non_black = np.where(img_array.sum(axis=2) > threshold)
        
        # Find the bounding box of non-black pixels
        y_min, y_max = non_black[0].min(), non_black[0].max()
        x_min, x_max = non_black[1].min(), non_black[1].max()
        
        # Crop the image to the bounding box
        cropped_img = img.crop((x_min, y_min, x_max + 1, y_max + 1))
        
        return cropped_img
        
    except Exception as e:
        print(f"Error cleaning {image_path}: {str(e)}")
        return None

def calculate_brightness(image_path):
    """Calculate the average brightness of an image."""
    try:
        # First clean the image
        img = clean_image(image_path)
        if img is None:
            return None
        
        # Convert image to grayscale
        gray_img = img.convert('L')
        
        # Calculate average pixel value (brightness)
        pixels = list(gray_img.getdata())
        average_brightness = sum(pixels) / len(pixels)
        
        # Return brightness percentage (0-100)
        return (average_brightness / 255) * 100
        
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return None

def analyze_images_in_directory(directory_path):
    """Analyze brightness for all images in the specified directory."""
    # Supported image formats
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        print(f"Directory '{directory_path}' not found.")
        return
    
    # Process each file in the directory
    for filename in os.listdir(directory_path):
        # Check if file is an image
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext in supported_formats:
            image_path = os.path.join(directory_path, filename)
            brightness = calculate_brightness(image_path)
            
            if brightness is not None:
                print(f"{filename}: Brightness level = {brightness:.2f}%")

def main():
    # Set the directory path
    images_directory = "images"
    
    print("Analyzing images in the 'images' directory...")
    analyze_images_in_directory(images_directory)

if __name__ == "__main__":
    main()
