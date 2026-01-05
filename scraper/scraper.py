#!/usr/bin/env python3
import json
import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime
from pathlib import Path

class StreamScraper:
    def __init__(self, channels_config):
        self.channels = channels_config['channels']
        self.streams = []
        self.output_dir = Path('../public')
        self.output_dir.mkdir(exist_ok=True)
    
    def scrape_youtube_stream(self, config):
        """Extract M3U8 from YouTube live"""
        try:
            video_id = config.get('youtube_id')
            if not video_id:
                return None
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(video_url, headers=headers, timeout=10)
            
            # Extract stream URL
            pattern = r'"hlsManifestUrl":"([^"]+)"'
            match = re.search(pattern, response.text)
            
            if match:
                url = match.group(1).replace('\\u0026', '&')
                return url
            
            return None
            
        except Exception as e:
            print(f"❌ Error scraping YouTube {config.get('youtube_id')}: {e}")
            return None
    
    def scrape_all(self):
        """Scrape all channels"""
        print("🔍 Starting stream scraping...")
        
        for channel in self.channels:
            print(f"  → {channel['name']}...", end=' ')
            stream_url = None
            
            if channel['source_type'] == 'youtube':
                stream_url = self.scrape_youtube_stream(channel['scrape_config'])
            elif channel['source_type'] == 'direct':
                stream_url = channel['scrape_config']['url']
            
            if stream_url:
                self.streams.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'category': channel['category'],
                    'logo': channel['logo'],
                    'url': stream_url,
                    'updated_at': datetime.utcnow().isoformat()
                })
                print("✅")
            else:
                print("❌")
        
        return self.streams
    
    def generate_m3u8(self):
        """Generate M3U8 playlist"""
        m3u8_content = "#EXTM3U\n"
        
        for stream in self.streams:
            m3u8_content += f'#EXTINF:-1 tvg-id="{stream["id"]}" '
            m3u8_content += f'tvg-name="{stream["name"]}" '
            m3u8_content += f'tvg-logo="{stream["logo"]}" '
            m3u8_content += f'group-title="{stream["category"].title()}",{stream["name"]}\n'
            m3u8_content += f'{stream["url"]}\n'
        
        return m3u8_content
    
    def save_outputs(self):
        """Save M3U8 and JSON"""
        m3u8_path = self.output_dir / 'playlist.m3u8'
        with open(m3u8_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_m3u8())
        
        json_path = self.output_dir / 'streams.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.utcnow().isoformat(),
                'total_streams': len(self.streams),
                'streams': self.streams
            }, f, indent=2)
        
        html_path = self.output_dir / 'index.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_index_html())
        
        print(f"\n✅ Generated {len(self.streams)} streams")

    def generate_index_html(self):
        """Generate web interface"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Live TV Streams</title>
    <style>
        body {{ font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; }}
        .info {{ text-align: center; margin-bottom: 30px; }}
        .channel-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }}
        .channel-card {{ background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 20px; text-align: center; }}
        .channel-logo {{ width: 80px; height: 80px; object-fit: contain; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📺 Live TV Streams</h1>
        <div class="info">
            <p>Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
            <p>Total Channels: {len(self.streams)}</p>
            <p><a href="/playlist.m3u8" style="color: white;">Download M3U8</a> | <a href="/streams.json" style="color: white;">View JSON</a></p>
        </div>
        <div class="channel-grid">
            {''.join([f'<div class="channel-card"><img src="{s["logo"]}" class="channel-logo"><h3>{s["name"]}</h3><span>{s["category"].title()}</span></div>' for s in self.streams])}
        </div>
    </div>
</body>
</html>"""

if __name__ == '__main__':
    # Try both paths (for local and Netlify)
    config_paths = ['../channels.json', 'channels.json']
    config = None
    
    for path in config_paths:
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                break
        except FileNotFoundError:
            continue
    
    if not config:
        print("❌ channels.json not found!")
        exit(1)
    
    scraper = StreamScraper(config)
    scraper.scrape_all()
    scraper.save_outputs()