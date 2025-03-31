#!/usr/bin/env python
from random import randint

from PIL import Image
import os

from pydantic import BaseModel

from crewai.flow import Flow, listen, start

import requests
import os
import json
from dotenv import load_dotenv
import time

from bs4 import BeautifulSoup
from urllib.parse import urlparse
import mimetypes

from web_scraper.src.web_scraper.crews.image_summarizer.image_summarizer import ImageSummarizerCrew

load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
MAX_RETRIES = 5

def get_default_headers():
    return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows"
        }


def get_base_url(url):
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    # Check if it's under a sub-path like '/blog' and include that
    if parsed.path.startswith('/blog'):
        base_url += '/blog'
    return base_url


def convert_avif_to(output_format, input_path, output_path=None):
    """
    Converts an AVIF image to JPG or PNG.

    Parameters:
        output_format (str): "jpg" or "png"
        input_path (str): Path to input .avif image
        output_path (str): Optional output path. If None, it saves next to input.
    """
    print(f"Converting {input_path} to {output_format}")
    if output_format.lower() not in ["jpg", "png"]:
        raise ValueError("Output format must be 'jpg' or 'png'")

    with Image.open(input_path) as im:
        rgb_im = im.convert("RGB")
        if not output_path:
            output_path = os.path.splitext(input_path)[0] + f".{output_format.lower()}"
        rgb_im.save(output_path)
        print(f"Saved: {output_path}")


class ScraperState(BaseModel):
    url: str = "https://creativecloud.adobe.com/cc/discover/article/build-dynamic-cityscapes-with-brian-yap?locale=es"
    markdown: str = ""
    links: list = []
    html: str = ""
    rawHtml: str = ""
    screenshot: str = ""
    downloaded_images: list = []
    image_summaries: list = []


class ScraperFlow(Flow[ScraperState]):

    @start()
    def scrape(self):
        try:
            base_url = "https://api.firecrawl.dev/v1/scrape"
            data = {
                "url": self.state.url,
                "formats": ["markdown", "links", "html", "rawHtml", "screenshot"],
                "includeTags": ["h1", "p", "a", ".main-content"],
                "excludeTags": ["#ad", "#footer"],
                "onlyMainContent": False,
                "waitFor": 10000,
                "timeout": 15000
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}"
            }
            
            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(base_url, headers=headers, json=data)
                    dataGot = json.loads(response.text)

                    os.makedirs("output", exist_ok=True)
                    os.makedirs(f"output/{self.flow_id}", exist_ok=True)

                    with open(f"output/{self.flow_id}/response.json", "w") as f:
                        f.write(json.dumps(dataGot))

                    self.state.markdown = dataGot["data"]["markdown"]
                    self.state.links = dataGot["data"]["links"]
                    self.state.html = dataGot["data"]["html"]
                    self.state.rawHtml = dataGot["data"]["rawHtml"]
                    self.state.screenshot = dataGot["data"]["screenshot"]

                    with open(f"output/{self.flow_id}/output.md", "w") as f:
                        f.write(self.state.markdown)
                    
                    with open(f"output/{self.flow_id}/output.html", "w") as f:
                        f.write(self.state.html)
                    
                    with open(f"output/{self.flow_id}/output_links.json", "w") as f:
                        f.write(json.dumps(self.state.links))
                    
                    break  # exit loop on success

                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == MAX_RETRIES - 1:
                        raise Exception(f"Error scraping after {MAX_RETRIES} attempts: {e}")
                    time.sleep(2)  # optional wait before retrying

            
        except requests.RequestException as e:
            raise Exception(f"Error scraping webpage: {str(e)}")
    
    @listen(scrape)
    def scrape_image(self):
        # Parse the raw HTML with BeautifulSoup
        soup = BeautifulSoup(self.state.rawHtml, 'html.parser')
        
        # Find all img tags
        img_tags = soup.find_all('img')
        
        # Create images directory if it doesn't exist
        img_dir = f"output/{self.flow_id}/images"
        os.makedirs(img_dir, exist_ok=True)
        
        downloaded_images = []
        
        for i, img in enumerate(img_tags):
            src = img.get('src')
            if not src:
                continue
                
            try:
                if src.startswith('/'):
                    src = get_base_url(self.state.url) + src
                elif src.startswith('./'):
                    src = get_base_url(self.state.url) + '/' + src[2:]
                    print(src)
                elif src.startswith('../'):
                    src = get_base_url(self.state.url) + '/' + src[3:]
                    print(src)
                    

                # Download image
                response = requests.get(src, headers=get_default_headers())
                if response.status_code != 200:
                    continue
                
                # Determine file extension from Content-Type or URL
                content_type = response.headers.get('Content-Type', '')
                ext = mimetypes.guess_extension(content_type) or os.path.splitext(urlparse(src).path)[1]
                if not ext:
                    ext = '.jpg'  # Default extension
                
                
                
                # Clean extension (remove query parameters if any)
                ext = ext.split('?')[0]
                
                # Generate filename
                filename = f"image_{i}{ext}"
                filepath = os.path.join(img_dir, filename)

                # Convert AVIF to JPG
                if ext == ".avif":
                    jpg_path = filepath.replace(".avif", ".jpg")
                    try:
                        convert_avif_to("jpg", filepath, jpg_path)
                        filepath = jpg_path  # update path to converted image
                    except Exception as e:
                        print(f"Failed to convert AVIF image {filepath}: {e}")
                        continue  # Skip this image
                else:
                    # Save image
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                
                downloaded_images.append({
                    'original_src': src,
                    'saved_path': filepath,
                    'content_type': content_type
                })

                self.state.downloaded_images.append((src, filepath))
                
                print(f"Downloaded image: {filename}")
                
            except Exception as e:
                print(f"Error downloading image {src}: {str(e)}")
                pass
        
        # Save image metadata
        with open(f"output/{self.flow_id}/image_metadata.json", "w") as f:
            json.dump(downloaded_images, f, indent=2)
        
        return f"Successfully downloaded {len(downloaded_images)} images"

    @listen(scrape_image)
    def summarize_images(self):
        """Summarizes the downloaded images."""
        print("Length of downloaded images: ", len(self.state.downloaded_images))
        if len(self.state.downloaded_images) > 0:
            # Create directory for image summaries
            save_dir = f"output/{self.flow_id}/image_summaries"
            os.makedirs(save_dir, exist_ok=True)
            
            # Summarize each image
            for i, (original_src, save_path) in enumerate(self.state.downloaded_images, 1):
                try:
                    # Check if the image is in a supported format
                    supported_formats = ['.png', '.jpeg', '.webp', '.gif', '.jpg', '.avif']
                    img_ext = os.path.splitext(save_path)[1].lower()
                    if img_ext in supported_formats:
                        # Generate summary
                        summarizer_crew = ImageSummarizerCrew()
                        print("Summarizing image: ", save_path)
                        summary = summarizer_crew.crew().kickoff(inputs={"image_path": save_path})
                        self.state.image_summaries.append((save_path, summary, original_src))
                        # Save summary
                        with open(f"{save_dir}/{i}.txt", "w") as f:
                            f.write(str(summary))  # Ensure it's a string
                        print(f"Summary saved to {save_dir}/{i}.txt")
                except Exception as e:
                    print(f"Error processing {i}. {save_path}: {str(e)}")
                    raise Exception(f"Error processing {i}. {save_path}: {str(e)}")
                
        return self.state
    
    @listen(summarize_images)
    def save_image_summaries(self):
        """Saves the image summaries to a file."""
        save_dir = f"output/{self.flow_id}/image_summaries"
        os.makedirs(save_dir, exist_ok=True)
        
        # Save summaries
        with open(f"{save_dir}/image_summaries.txt", "w") as f:
            for i, (save_path, summary, original_src) in enumerate(self.state.image_summaries, 1):
                ext = os.path.splitext(save_path)[1].lower()
                if ext in ['.png', '.jpeg', '.jpg', '.gif']:
                    f.write(f"Image {i}:\nPath: {save_path}\nSource: {original_src}\nSummary: {summary}\n\n")
                print(f"Summary {i} saved to {save_dir}/image_summaries.txt")
        
        return self.state
    
    @listen(save_image_summaries)
    def finalize(self):
        # Convert image summaries to serializable format
        serializable_summaries = []
        for path, summary, original_src in self.state.image_summaries:
            serializable_summaries.append({
                "image_path": path,
                "summary": str(summary),  # Convert CrewOutput to string
                "original_src": original_src
            })

        final_output = {
            "image_summaries": serializable_summaries,
            "downloaded_images": [
                {"url": url, "path": path} 
                for url, path in self.state.downloaded_images
            ],
            "flow_id": self.flow_id,
            "markdown": self.state.markdown
        }

        with open(f"output/{self.flow_id}/final_output.json", "w") as f:
            json.dump(final_output, f, indent=2)
        return final_output

    
def kickoff():
    scraper_flow = ScraperFlow()
    scraper_flow.kickoff()


def plot():
    scraper_flow = ScraperFlow()
    scraper_flow.plot()


if __name__ == "__main__":
    kickoff()
    plot()
