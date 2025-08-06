# Tick Grading Backend

A FastAPI-based backend for automated question parsing and response processing.

## Features

### Question Parsing

- PDF to image conversion
- Diagram and table detection using Doc-YOLO
- Question text extraction using LLM OCR
- Marks extraction
- Page diagram detection

### Response Processing

- Margin cropping using Sobel edge detection
- **Image Enhancement** - Sequential deblur + binarization before OCR processing
- Amazon Textract integration for OCR
- Gemini AI integration for answer extraction
- Question cropping and merging
- Cloudinary integration for image storage

## Image Enhancement

The response processing workflow now includes automatic sequential image enhancement before sending images to Amazon Textract. This improves OCR accuracy by:

1. **Deblurring**: Reducing image blur for clearer text
2. **Binarization**: Converting images to black and white for better text contrast

### Workflow

1. Margin cropping detects and crops the left margin
2. **NEW**: Deblur enhancement is applied to the cropped image
3. **NEW**: Binarization enhancement is applied to the deblurred image
4. **NEW**: Final enhanced image is sent to Amazon Textract
5. Textract processes the enhanced image for better OCR results
6. Gemini AI extracts answer labels from the enhanced image
7. Results are merged and processed

## Environment Variables

Required environment variables:

- `GEMINI_API_KEY`: Google Gemini API key
- `AWS_ACCESS_KEY_ID`: AWS access key for Textract
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for Textract
- `AWS_REGION`: AWS region for Textract
- `CLOUDINARY_CLOUD_NAME`: Cloudinary cloud name
- `CLOUDINARY_API_KEY`: Cloudinary API key
- `CLOUDINARY_API_SECRET`: Cloudinary API secret

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables

3. Run the application:

```bash
uvicorn app.main:app --reload
```

## API Endpoint

- `POST /crop-margins`: Process response images with margin cropping and image enhancement
- `POST /parse-questions`: Parse question PDFs
- `GET /logs/`: View processing logs

## Dependencies

Key dependencies include:

- FastAPI
- TensorFlow (for image enhancement models)
- OpenCV
- PIL/Pillow
- NumPy
- Matplotlib
- AWS Boto3 (for Textract)
- Google Generative AI
- Cloudinary
