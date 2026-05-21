import sys
import os
import xml.sax.saxutils as saxutils
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
def generate_rss(html_content, series_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    items_xml = []
    
    # TVer episode containers
    items = soup.select('a[href^="/episodes/"], a[href^="/live/"]')
    
    seen_urls = set()
    
    for item in items:
        if 'href' not in item.attrs:
            continue
            
        href = item['href']
        item_url = "https://tver.jp" + href
        escaped_url = item_url.replace('&', '&amp;')
        
        if item_url in seen_urls:
            continue
        seen_urls.add(item_url)
        
        # Extract title and image
        img_elem = item.select_one('img')
        img_url = img_elem['src'] if img_elem and 'src' in img_elem.attrs else ""
        item_title = img_elem['alt'] if img_elem and 'alt' in img_elem.attrs else "No Title"
        
        # Fallback for title if alt is empty
        if not item_title or item_title == "No Title":
            title_elem = item.select_one('[class*="title"]')
            item_title = title_elem.text if title_elem else "No Title"
        
        # Sub info (broadcast date, end date)
        subinfos = item.select('[class*="subInfo__"]')
        info_texts = [info.text for info in subinfos]
        
        item_desc = "<br>".join(info_texts)
        if img_url:
            item_desc = f'<img src="{img_url}"><br>' + item_desc
            
        # Escape for XML
        item_title_esc = saxutils.escape(item_title)
        
        item_xml = f"""    <item>
      <title>{item_title_esc}</title>
      <link>{item_url}</link>
      <guid>{item_url}</guid>
      <description><![CDATA[{item_desc}]]></description>
    </item>"""
        items_xml.append(item_xml)
        
    items_str = "\n".join(items_xml)
    
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>TVer Series RSS: {series_url}</title>
    <link>{series_url}</link>
    <description>TVer Episode RSS Feed generated from Playwright</description>
{items_str}
  </channel>
</rss>"""
    return rss_xml
def process_urls():
    if not os.path.exists('urls.txt'):
        print("urls.txt not found. Please create one with TVer series URLs.")
        sys.exit(1)
        
    with open('urls.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
    if not urls:
        print("No URLs found in urls.txt")
        return
        
    print(f"Found {len(urls)} URLs to process.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for url in urls:
            print(f"Processing: {url}")
            try:
                # Extract series ID from URL (e.g., https://tver.jp/series/sr7x3ce7ak -> sr7x3ce7ak)
                series_id = url.split('/')[-1]
                
                page.goto(url)
                
                # Wait for the episode list to load (either episodes or main container)
                try:
                    page.wait_for_selector('a[href^="/episodes/"], a[href^="/live/"], [class*="SeasonEpisodeList"]', timeout=10000)
                except Exception as e:
                    print(f"  Warning: Timeout waiting for episodes on {url}. It might have no episodes or the layout changed.")
                    
                html_content = page.content()
                
                rss_xml = generate_rss(html_content, url)
                
                output_filename = f"feed_{series_id}.xml"
                with open(output_filename, 'w', encoding='utf-8') as out_f:
                    out_f.write(rss_xml)
                    
                print(f"  Saved to {output_filename}")
                
            except Exception as e:
                print(f"  Error processing {url}: {e}")
                
        browser.close()
if __name__ == '__main__':
    process_urls()
