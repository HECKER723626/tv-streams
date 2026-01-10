#!/usr/bin/env python3
import json
import requests
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

class StreamScraper:
    def __init__(self, channels_config):
        self.channels = channels_config['channels']
        self.genres = channels_config.get('genres', {})
        self.streams = []
        self.output_dir = Path('../public')
        self.output_dir.mkdir(exist_ok=True)
    
    def get_logo_url(self, logo_filename):
        """Convert logo filename to full URL"""
        if logo_filename.startswith('http'):
            return logo_filename
        
        encoded = quote(logo_filename)
        return f"https://hecker723626.github.io/tv-streams/logos/{encoded}"
    
    def detect_source_type(self, url):
        """Auto-detect source type from URL"""
        if not url:
            return 'unknown'
        
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            if '/live' in url_lower or '/channel/' in url_lower:
                return 'youtube_live'
            elif '/embed/' in url_lower or '/watch' in url_lower:
                return 'youtube_embed'
        elif 'mcaster.tv' in url_lower:
            return 'mcaster_iframe'
        elif 'stmify.com' in url_lower or 'cdn.stmify.com' in url_lower:
            return 'stmify_iframe'
        elif url_lower.endswith('.m3u8') or 'm3u8' in url_lower:
            return 'direct_m3u8'
        else:
            return 'iframe'
    
    def extract_youtube_m3u8(self, video_url):
        """Extract M3U8 from YouTube URL"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(video_url, headers=headers, timeout=10)
            
            pattern = r'"hlsManifestUrl":"([^"]+)"'
            match = re.search(pattern, response.text)
            
            if match:
                return match.group(1).replace('\\u0026', '&')
            
            video_id = None
            if '/watch?v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif '/embed/' in video_url:
                video_id = video_url.split('/embed/')[1].split('?')[0]
            elif '/channel/' in video_url and '/live' in video_url:
                vid_match = re.search(r'"videoId":"([^"]+)"', response.text)
                if vid_match:
                    video_id = vid_match.group(1)
            
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"
            
            return None
        except Exception as e:
            print(f"YouTube error: {e}")
            return None
    
    def process_source(self, source_url):
        """Process a source URL and return playable URL"""
        if not source_url:
            return None
        
        if source_url.startswith('//'):
            source_url = 'https:' + source_url
        elif not source_url.startswith('http'):
            source_url = 'https://' + source_url
        
        source_type = self.detect_source_type(source_url)
        
        if source_type in ['youtube_live', 'youtube_embed']:
            processed = self.extract_youtube_m3u8(source_url)
            return processed if processed else source_url
        
        return source_url
    
    def scrape_all(self):
        """Scrape all channels"""
        print("🔍 Starting stream scraping...")
        print(f"📊 Total channels: {len(self.channels)}\n")
        
        success_count = 0
        fail_count = 0
        
        for idx, channel in enumerate(self.channels, 1):
            name = channel.get('name', 'Unknown')
            print(f"[{idx}/{len(self.channels)}] {name}...", end=' ')
            
            sources_dict = channel.get('sources', {})
            if not sources_dict:
                print("❌ (no sources)")
                fail_count += 1
                continue
            
            processed_sources = {}
            for src_key, src_url in sources_dict.items():
                processed_url = self.process_source(src_url)
                if processed_url:
                    processed_sources[src_key] = {
                        'url': processed_url,
                        'type': self.detect_source_type(processed_url)
                    }
            
            if processed_sources:
                first_source = list(processed_sources.values())[0]
                
                self.streams.append({
                    'id': channel.get('id', name.lower().replace(' ', '-')),
                    'name': name,
                    'logo': self.get_logo_url(channel.get('logo', 'placeholder.png')),
                    'genre': channel.get('genre', 'entertainment'),
                    'url': first_source['url'],
                    'source_type': first_source['type'],
                    'sources': processed_sources,
                    'updated_at': datetime.utcnow().isoformat()
                })
                print(f"✅ ({len(processed_sources)} sources)")
                success_count += 1
            else:
                print("❌ (all sources failed)")
                fail_count += 1
        
        print(f"\n📈 Results: {success_count} successful, {fail_count} failed")
        return self.streams
    
    def generate_m3u8(self):
        """Generate M3U8 playlist"""
        m3u8_content = "#EXTM3U\n"
        
        for stream in self.streams:
            genre_name = self.genres.get(stream['genre'], {}).get('name', stream['genre'].title())
            m3u8_content += f'#EXTINF:-1 tvg-id="{stream["id"]}" '
            m3u8_content += f'tvg-name="{stream["name"]}" '
            m3u8_content += f'tvg-logo="{stream["logo"]}" '
            m3u8_content += f'group-title="{genre_name}",{stream["name"]}\n'
            m3u8_content += f'{stream["url"]}\n'
        
        return m3u8_content
    
    def save_outputs(self):
        """Save all output files"""
        m3u8_path = self.output_dir / 'playlist.m3u8'
        with open(m3u8_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_m3u8())
        
        json_path = self.output_dir / 'streams.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.utcnow().isoformat(),
                'total_streams': len(self.streams),
                'genres': self.genres,
                'streams': self.streams
            }, f, indent=2, ensure_ascii=False)
        
        html_path = self.output_dir / 'index.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_index_html())
        
        print(f"\n✅ Generated {len(self.streams)} streams")
        print(f"📁 Saved to: {self.output_dir.absolute()}")

    def generate_index_html(self):
        """Generate modern web player interface with FIXED source switching"""
        by_genre = {}
        for stream in self.streams:
            genre = stream['genre']
            if genre not in by_genre:
                by_genre[genre] = []
            by_genre[genre].append(stream)
        
        tabs_html = ''
        content_html = ''
        
        for idx, (genre, channels) in enumerate(by_genre.items()):
            active = 'active' if idx == 0 else ''
            genre_info = self.genres.get(genre, {'name': genre.title(), 'icon': '📺'})
            
            tabs_html += f'''
            <button class="tab-btn {active}" data-genre="{genre}">
                {genre_info["icon"]} {genre_info["name"]} ({len(channels)})
            </button>'''
            
            content_html += f'<div class="genre-content {active}" data-genre="{genre}">'
            content_html += '<div class="channel-grid">'
            
            for ch in channels:
                num_sources = len(ch.get('sources', {}))
                
                content_html += f'''
                <div class="channel-card" data-channel='{json.dumps(ch, ensure_ascii=False)}'>
                    <img src="{ch['logo']}" class="channel-logo" alt="{ch['name']}" 
                         onerror="this.src='https://via.placeholder.com/100x100/667eea/ffffff?text={ch['name'][:2]}'">
                    <h3>{ch['name']}</h3>
                    <span class="badge">{num_sources} source{'s' if num_sources > 1 else ''}</span>
                </div>'''
            
            content_html += '</div></div>'
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live TV - {len(self.streams)} Channels</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{ text-align: center; margin-bottom: 30px; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .stats {{ font-size: 1rem; opacity: 0.9; margin-top: 10px; }}
        .stats a {{ color: #fff; text-decoration: underline; }}
        
        .tabs {{ display: flex; gap: 10px; margin-bottom: 30px; flex-wrap: wrap; justify-content: center; }}
        .tab-btn {{ 
            background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.3);
            padding: 12px 24px; border-radius: 25px; color: white; cursor: pointer;
            font-size: 1rem; font-weight: 500; transition: all 0.3s;
        }}
        .tab-btn:hover {{ background: rgba(255,255,255,0.3); transform: translateY(-2px); }}
        .tab-btn.active {{ background: rgba(255,255,255,0.4); font-weight: bold; }}
        
        .genre-content {{ display: none; }}
        .genre-content.active {{ display: block; }}
        
        .channel-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); 
            gap: 20px; 
        }}
        .channel-card {{ 
            background: rgba(255,255,255,0.15); border-radius: 15px; padding: 15px; 
            text-align: center; cursor: pointer; transition: all 0.3s;
            backdrop-filter: blur(10px); border: 2px solid rgba(255,255,255,0.1);
        }}
        .channel-card:hover {{ 
            transform: translateY(-5px); 
            background: rgba(255,255,255,0.25);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .channel-logo {{ 
            width: 80px; height: 80px; object-fit: contain; margin-bottom: 10px;
            border-radius: 10px; background: white; padding: 8px;
        }}
        h3 {{ font-size: 0.9rem; margin-bottom: 8px; font-weight: 600; }}
        .badge {{
            display: inline-block; background: rgba(255,255,255,0.2);
            padding: 4px 10px; border-radius: 12px; font-size: 0.7rem;
        }}
        
        .player-modal {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.95); z-index: 1000; padding: 20px;
        }}
        .player-modal.active {{ display: flex; align-items: center; justify-content: center; flex-direction: column; }}
        
        .player-header {{
            width: 100%; max-width: 1200px; display: flex;
            justify-content: space-between; align-items: center; margin-bottom: 20px;
        }}
        .player-title {{ font-size: 1.5rem; font-weight: bold; }}
        .player-controls {{ display: flex; gap: 10px; align-items: center; }}
        
        .source-btn {{
            background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.3);
            color: white; padding: 8px 16px; border-radius: 20px; cursor: pointer;
            font-size: 0.9rem; transition: all 0.3s;
        }}
        .source-btn:hover {{ background: rgba(255,255,255,0.3); }}
        .source-btn.active {{ background: rgba(255,255,255,0.4); font-weight: bold; border-color: rgba(255,255,255,0.6); }}
        
        .close-btn {{
            background: rgba(255,0,0,0.8); border: none; color: white;
            font-size: 1.5rem; width: 45px; height: 45px; border-radius: 50%;
            cursor: pointer; transition: all 0.3s;
        }}
        .close-btn:hover {{ background: rgba(255,0,0,1); transform: scale(1.1); }}
        
        .player-container {{ 
            width: 100%; max-width: 1200px; background: #000; 
            border-radius: 10px; overflow: hidden; position: relative;
        }}
        .player-iframe {{ width: 100%; height: 80vh; border: none; display: block; }}
        
        .loading-spinner {{
            display: none; position: absolute; top: 50%; left: 50%;
            transform: translate(-50%, -50%); color: white; font-size: 1.2rem;
        }}
        .loading-spinner.active {{ display: block; }}
        
        footer {{ text-align: center; margin-top: 50px; padding: 20px; opacity: 0.8; }}
        
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.8rem; }}
            .channel-grid {{ grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }}
            .player-header {{ flex-direction: column; gap: 15px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📺 Live TV Streams</h1>
            <div class="stats">
                <p>Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                <p><strong>{len(self.streams)}</strong> Channels • Updates Every 6 Hours</p>
                <p><a href="/playlist.m3u8">📥 M3U8</a> | <a href="/streams.json">🔗 JSON API</a></p>
            </div>
        </header>
        
        <div class="tabs">{tabs_html}</div>
        {content_html}
        
        <footer><p>🔄 Automatic updates every 6 hours</p></footer>
    </div>
    
    <div class="player-modal" id="playerModal">
        <div class="player-header">
            <div class="player-title" id="playerTitle"></div>
            <div class="player-controls">
                <div id="sourceBtns"></div>
                <button class="close-btn" onclick="closePlayer()">✕</button>
            </div>
        </div>
        <div class="player-container">
            <div class="loading-spinner" id="loadingSpinner">Loading...</div>
            <iframe class="player-iframe" id="playerFrame" allowfullscreen allow="autoplay"></iframe>
        </div>
    </div>
    
    <script>
        let currentChannel = null;
        let currentSourceKey = null;
        
        // Genre tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.onclick = () => {{
                const genre = btn.dataset.genre;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.genre-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.querySelector(`.genre-content[data-genre="${{genre}}"]`).classList.add('active');
            }};
        }});
        
        // Channel card click
        document.querySelectorAll('.channel-card').forEach(card => {{
            card.onclick = () => {{
                currentChannel = JSON.parse(card.dataset.channel);
                openPlayer(currentChannel);
            }};
        }});
        
        function openPlayer(channel) {{
            console.log('Opening channel:', channel.name);
            console.log('Available sources:', channel.sources);
            
            document.getElementById('playerTitle').textContent = channel.name;
            
            const sourcesContainer = document.getElementById('sourceBtns');
            sourcesContainer.innerHTML = '';
            
            const sources = channel.sources || {{}};
            const sourceKeys = Object.keys(sources);
            
            // Always create source buttons if multiple sources exist
            if (sourceKeys.length > 1) {{
                sourceKeys.forEach((key, idx) => {{
                    const btn = document.createElement('button');
                    btn.className = 'source-btn' + (idx === 0 ? ' active' : '');
                    btn.textContent = key.toUpperCase();
                    btn.dataset.sourceKey = key;  // Store the actual source key
                    btn.onclick = () => loadSource(key);
                    sourcesContainer.appendChild(btn);
                }});
            }}
            
            // Load first source by default
            if (sourceKeys.length > 0) {{
                loadSource(sourceKeys[0]);
            }}
            
            document.getElementById('playerModal').classList.add('active');
        }}
        
        function loadSource(sourceKey) {{
            console.log('Loading source:', sourceKey);
            
            // Validate source exists
            if (!currentChannel || !currentChannel.sources || !currentChannel.sources[sourceKey]) {{
                console.error('Source not found:', sourceKey);
                alert('This source is not available');
                return;
            }}
            
            const source = currentChannel.sources[sourceKey];
            console.log('Source data:', source);
            
            currentSourceKey = sourceKey;
            
            // Update active button
            document.querySelectorAll('.source-btn').forEach(btn => {{
                const isActive = btn.dataset.sourceKey === sourceKey;
                btn.classList.toggle('active', isActive);
            }});
            
            // Show loading
            const loadingSpinner = document.getElementById('loadingSpinner');
            const playerFrame = document.getElementById('playerFrame');
            loadingSpinner.classList.add('active');
            
            // Handle different source types
            if (source.type === 'direct_m3u8') {{
                // For direct M3U8, open in new tab
                window.open(source.url, '_blank');
                loadingSpinner.classList.remove('active');
            }} else {{
                // For iframe sources, load in player
                // Clear previous iframe first
                playerFrame.src = '';
                
                // Small delay to ensure clean state
                setTimeout(() => {{
                    playerFrame.src = source.url;
                    
                    // Hide loading after delay
                    setTimeout(() => {{
                        loadingSpinner.classList.remove('active');
                    }}, 2000);
                }}, 100);
            }}
        }}
        
        function closePlayer() {{
            document.getElementById('playerModal').classList.remove('active');
            document.getElementById('playerFrame').src = '';
            document.getElementById('loadingSpinner').classList.remove('active');
            currentChannel = null;
            currentSourceKey = null;
        }}
        
        // Close on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closePlayer();
        }});
        
        // Prevent closing when clicking inside player
        document.querySelector('.player-container').addEventListener('click', (e) => {{
            e.stopPropagation();
        }});
        
        // Close when clicking outside player
        document.getElementById('playerModal').addEventListener('click', (e) => {{
            if (e.target.id === 'playerModal') {{
                closePlayer();
            }}
        }});
    </script>
</body>
</html>'''

if __name__ == '__main__':
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
