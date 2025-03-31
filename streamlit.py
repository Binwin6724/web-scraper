import streamlit as st
import time
import asyncio
from web_scraper.src.web_scraper.main import ScraperFlow

st.set_page_config(layout="wide")

def format_time(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    if minutes > 0:
        return f"{minutes} min {remaining_seconds:.2f} sec"
    return f"{remaining_seconds:.2f} sec"

async def get_scraper_response(url):
    start_time = time.time()
    response = await ScraperFlow().kickoff_async(inputs={"url": url, "type": "url"})
    elapsed_time = time.time() - start_time
    response_json = response
    return response_json, elapsed_time

def main():
    st.title("Web Scraper with Image Analysis")
    
    # URL input
    url = st.text_input("Enter URL to scrape:", placeholder="https://example.com")

    
    if st.button("Scrape"):
        with st.spinner("Scraping website and analyzing images..."):
            try:
                data, elapsed_time = asyncio.run(get_scraper_response(url))
                st.info(f"API Response Time: {format_time(elapsed_time)}")
                
                # Create two columns
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.header("Article Content")
                    st.markdown(data["markdown"])
                
                with col2:
                    st.header("Images and Summaries")
                    
                    # Create a grid layout for images
                    for img_data in data["image_summaries"]:
                        st.write("---")
                        
                        # Get image info
                        img_path = img_data["image_path"]
                        summary = img_data["summary"]
                        original_src = img_data["original_src"]
                        
                        # Display original source URL
                        st.write(f"**Source URL:** [{original_src}]({original_src})")
                        
                        try:
                            st.image(original_src, caption="Scraped Image", use_container_width=True)
                        except Exception as e:
                            st.error(f"Error loading image: {str(e)}")
                        
                        # Display image summary
                        st.write("**Image Summary:**")
                        st.write(summary)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()