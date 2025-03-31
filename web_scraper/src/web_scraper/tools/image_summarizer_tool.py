import os
import base64
from typing import Any, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from openai import OpenAI  # Import the OpenAI client directly

class ImageSummarizerToolSchema(BaseModel):
    """Input schema for ImageSummarizerTool."""
    image_path: str = Field(..., description="URL or local file path to the image file to be summarized")

class ImageSummarizerTool(BaseTool):
    name: str = "Image Content Summarizer"
    description: str = "A tool that uses OpenAI Vision API to identify and describe the content of an image."
    args_schema: Type[BaseModel] = ImageSummarizerToolSchema

    def _run(self, **kwargs: Any) -> Any:
        image_path = kwargs.get("image_path")
        if not image_path:
            return "Error: No image path provided."
        
        return self.identify_image(image_path)

    def identify_image(self, image_path: str):
        """Uses OpenAI Vision API to identify the content of an image."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Error: OpenAI API key not found."

        try:
            # Initialize the OpenAI client with API key
            client = OpenAI(api_key=api_key)
            
            # Determine whether the input is a local file or a URL
            if os.path.exists(image_path):
                # Convert local image to base64
                with open(image_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode("utf-8")
                extension = os.path.splitext(image_path)[1]
                image_url = f"data:image/{extension};base64,{img_data}"
            else:
                # Assume input is a URL
                image_url = image_path
            
            # Call the OpenAI API with the current client syntax
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using vision-capable model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in detail for content generation purposes."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            # Extract the description from the response
            description = response.choices[0].message.content
            return description
        
        except Exception as e:
            return f"Error processing image: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Async not implemented")
