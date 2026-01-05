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
    
    def scrape_youtube_live(self, config):
        """Extract M3U8 from YouTube live using channel or handle"""
        try:
            # Try channel ID first
            channel_id = config.get('youtube_channel_id')
            if channel_id:
                # Get channel's live stream page
                channel_url = f"https://www.youtube.com/channel/{channel_id}/live"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(channel_url, headers=headers, timeout=10)
                
                # Extract live video ID
                video_id_match = re.search(r'"videoId":"([^"]+)"', response.text)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    return self.extract_youtube_m3u8(video_id)
            
            return None
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def extract_youtube_m3u8(self, video_id):
        """Extract M3U8 URL from YouTube video ID"""
        try:
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
        except:
            return None
    
    def scrape_youtube_embed(self, config):
        """Extract video ID from YouTube embed URL"""
        try:
            embed_url = config.get('youtube_embed_url', '')
            # Extract video ID from embed URL: /embed/VIDEO_ID
            video_id_match = re.search(r'/embed/([a-zA-Z0-9_-]+)', embed_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                return self.extract_youtube_m3u8(video_id)
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def scrape_iframe_stream(self, config, source_type):
        """
        For iframe sources, return the iframe URL directly
        Android apps and web players can embed these
        """
        try:
            iframe_url = config.get('iframe_url', '')
            if not iframe_url:
                return None
            
            # Ensure URL has protocol
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            elif not iframe_url.startswith('http'):
                iframe_url = 'https://' + iframe_url
            
            # Return iframe URL - apps will handle embedding
            return iframe_url
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def scrape_all(self):
        """Scrape all channels"""
        print("🔍 Starting stream scraping...")
        print(f"📊 Total channels to process: {len(self.channels)}\n")
        
        success_count = 0
        fail_count = 0
        
        for idx, channel in enumerate(self.channels, 1):
            print(f"[{idx}/{len(self.channels)}] {channel['name']}...", end=' ')
            stream_url = None
            
            source_type = channel.get('source_type', '')
            
            if source_type == 'youtube_live':
                stream_url = self.scrape_youtube_live(channel['scrape_config'])
            elif source_type == 'youtube_embed':
                stream_url = self.scrape_youtube_embed(channel['scrape_config'])
            elif source_type == 'direct':
                stream_url = channel['scrape_config'].get('url')
            elif source_type in ['mcaster_iframe', 'stmify_iframe']:
                stream_url = self.scrape_iframe_stream(channel['scrape_config'], source_type)
            
            if stream_url:
                self.streams.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'name_bn': channel.get('name_bn', channel['name']),
                    'country': channel.get('country', 'International'),
                    'category': channel['category'],
                    'logo': channel['logo'],
                    'url': stream_url,
                    'source_type': source_type,
                    'updated_at': datetime.utcnow().isoformat()
                })
                print("✅")
                success_count += 1
            else:
                print("❌")
                fail_count += 1
        
        print(f"\n📈 Results: {success_count} successful, {fail_count} failed")
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
            }, f, indent=2, ensure_ascii=False)
        
        html_path = self.output_dir / 'index.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_index_html())
        
        print(f"\n✅ Generated {len(self.streams)} streams")
        print(f"📁 Files saved to: {self.output_dir.absolute()}")

    def generate_index_html(self):
        """Generate web interface with iframe support"""
        # Group channels by category
        by_category = {}
        for stream in self.streams:
            cat = stream['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(stream)
        
        # Generate category tabs HTML
        category_tabs = ''
        category_content = ''
        
        for idx, (cat, channels) in enumerate(by_category.items()):
            active = 'active' if idx == 0 else ''
            category_tabs += f'<button class="tab-btn {active}" data-category="{cat}">{cat.title()} ({len(channels)})</button>'
            
            category_content += f'<div class="category-content {active}" data-category="{cat}">'
            category_content += '<div class="channel-grid">'
            
            for ch in channels:
                # Determine if it's iframe or direct stream
                is_iframe = ch['source_type'] in ['mcaster_iframe', 'stmify_iframe']
                play_type = 'iframe' if is_iframe else 'direct'
                
                category_content += f'''
                <div class="channel-card" data-url="{ch['url']}" data-type="{play_type}" data-name="{ch['name']}">
                    <img src="{ch['logo']}" class="channel-logo" alt="{ch['name']}">
                    <h3>{ch['name']}</h3>
                    <span class="country">{ch['country']}</span>
                </div>
                '''
            
            category_content += '</div></div>'
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live TV Streams - {len(self.streams)} Channels</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        
        header {{ text-align: center; margin-bottom: 30px; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .stats {{ font-size: 1.1rem; opacity: 0.9; }}
        .stats a {{ color: #fff; text-decoration: underline; }}
        
        .tabs {{ 
            display: flex; 
            gap: 10px; 
            margin-bottom: 30px; 
            flex-wrap: wrap;
            justify-content: center;
        }}
        .tab-btn {{ 
            background: rgba(255,255,255,0.2); 
            border: none; 
            padding: 12px 24px; 
            border-radius: 25px;
            color: white;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }}
        .tab-btn:hover {{ background: rgba(255,255,255,0.3); }}
        .tab-btn.active {{ background: rgba(255,255,255,0.4); font-weight: bold; }}
        
        .category-content {{ display: none; }}
        .category-content.active {{ display: block; }}
        
        .channel-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 20px; 
        }}
        .channel-card {{ 
            background: rgba(255,255,255,0.15); 
            border-radius: 15px; 
            padding: 20px; 
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            backdrop-filter: blur(10px);
        }}
        .channel-card:hover {{ 
            transform: translateY(-5px); 
            background: rgba(255,255,255,0.25);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .channel-logo {{ 
            width: 100px; 
            height: 100px; 
            object-fit: contain; 
            margin-bottom: 15px;
            border-radius: 10px;
            background: white;
            padding: 10px;
        }}
        h3 {{ font-size: 1rem; margin-bottom: 8px; }}
        .country {{ font-size: 0.85rem; opacity: 0.8; }}
        
        .player-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            padding: 20px;
        }}
        .player-modal.active {{ display: flex; align-items: center; justify-content: center; }}
        .player-container {{
            width: 100%;
            max-width: 1200px;
            position: relative;
        }}
        .close-btn {{
            position: absolute;
            top: -40px;
            right: 0;
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 2rem;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 1001;
        }}
        .player-iframe {{
            width: 100%;
            height: 80vh;
            border: none;
            border-radius: 10px;
        }}
        
        footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📺 Live TV Streams</h1>
            <div class="stats">
                <p>Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                <p>Total Channels: <strong>{len(self.streams)}</strong></p>
                <p><a href="/playlist.m3u8">Download M3U8</a> | <a href="/streams.json">View JSON API</a></p>
            </div>
        </header>
        
        <div class="tabs">
            {category_tabs}
        </div>
        
        {category_content}
        
        <footer>
            <p>Streams update every 30 minutes • Data for Android & Web apps</p>
        </footer>
    </div>
    
    <!-- Player Modal -->
    <div class="player-modal" id="playerModal">
        <div class="player-container">
            <button class="close-btn" onclick="closePlayer()">×</button>
            <iframe class="player-iframe" id="playerFrame" allowfullscreen></iframe>
        </div>
    </div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const category = btn.dataset.category;
                
                // Update active states
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.category-content').forEach(c => c.classList.remove('active'));
                
                btn.classList.add('active');
                document.querySelector(`.category-content[data-category="${{category}}"]`).classList.add('active');
            }});
        }});
        
        // Channel card click - play stream
        document.querySelectorAll('.channel-card').forEach(card => {{
            card.addEventListener('click', () => {{
                const url = card.dataset.url;
                const type = card.dataset.type;
                const name = card.dataset.name;
                
                if (type === 'iframe') {{
                    // Open iframe in modal
                    document.getElementById('playerFrame').src = url;
                    document.getElementById('playerModal').classList.add('active');
                }} else {{
                    // Direct M3U8 - open in new tab or suggest VLC
                    window.open(url, '_blank');
                }}
            }});
        }});
        
        function closePlayer() {{
            document.getElementById('playerModal').classList.remove('active');
            document.getElementById('playerFrame').src = '';
        }}
        
        // Close on ESC key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closePlayer();
        }});
    </script>
</body>
</html>'''

if __name__ == '__main__':
    # Try both paths (for local and GitHub Actions)
    config_paths = ['../channels.json', 'channels.json']
    config = None
    
    for path in config_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
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
