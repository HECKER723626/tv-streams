#!/usr/bin/env python3
"""
Telegram to Video Link Converter
Converts Telegram video links to embeddable URLs for static hosting
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class TelegramVideoConverter:
    """Convert Telegram video links to embeddable format"""
    
    def __init__(self, output_dir='../public'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.anime_data = []
        self.movie_data = []
    
    def convert_telegram_link(self, tg_link: str) -> Optional[Dict[str, str]]:
        """
        Convert Telegram link to usable video URL
        Supports:
        - t.me/channel/post
        - t.me/c/channel/post
        - Direct video file links
        """
        if not tg_link:
            return None
        
        # Clean the link
        tg_link = tg_link.strip()
        
        # Pattern matching for different Telegram link formats
        patterns = [
            r't\.me/([^/]+)/(\d+)',           # t.me/channel/123
            r't\.me/c/(\d+)/(\d+)',           # t.me/c/123456/789
            r'telegram\.me/([^/]+)/(\d+)',    # telegram.me/channel/123
        ]
        
        for pattern in patterns:
            match = re.search(pattern, tg_link)
            if match:
                channel = match.group(1)
                post_id = match.group(2)
                
                # Generate embed URL using various Telegram embed services
                return {
                    'original': tg_link,
                    'embed_url': f"https://t.me/{channel}/{post_id}?embed=1&mode=tme",
                    'preview_url': f"https://t.me/{channel}/{post_id}",
                    'type': 'telegram_embed'
                }
        
        # If it's already a direct video link
        if tg_link.startswith('http') and any(ext in tg_link.lower() for ext in ['.mp4', '.mkv', '.avi']):
            return {
                'original': tg_link,
                'embed_url': tg_link,
                'preview_url': tg_link,
                'type': 'direct_video'
            }
        
        return None
    
    def add_anime(self, anime_data: Dict) -> bool:
        """
        Add anime entry
        Expected format:
        {
            "id": "one-piece",
            "name": "One Piece",
            "image": "https://...",
            "genre": ["Action", "Adventure"],
            "description": "...",
            "type": "series",
            "episodes": [
                {
                    "number": 1,
                    "title": "Episode 1",
                    "telegram_link": "t.me/channel/123"
                }
            ],
            "related": {
                "previous_season": null,
                "next_season": "one-piece-2"
            }
        }
        """
        try:
            # Validate required fields
            required = ['id', 'name', 'type']
            if not all(field in anime_data for field in required):
                print(f"❌ Missing required fields: {required}")
                return False
            
            # Convert Telegram links for episodes
            if anime_data.get('type') == 'series' and 'episodes' in anime_data:
                for episode in anime_data['episodes']:
                    if 'telegram_link' in episode:
                        converted = self.convert_telegram_link(episode['telegram_link'])
                        if converted:
                            episode['video_url'] = converted['embed_url']
                            episode['video_type'] = converted['type']
            elif anime_data.get('type') == 'standalone' and 'telegram_link' in anime_data:
                converted = self.convert_telegram_link(anime_data['telegram_link'])
                if converted:
                    anime_data['video_url'] = converted['embed_url']
                    anime_data['video_type'] = converted['type']
            
            anime_data['updated_at'] = datetime.utcnow().isoformat()
            self.anime_data.append(anime_data)
            print(f"✅ Added anime: {anime_data['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding anime: {e}")
            return False
    
    def add_movie(self, movie_data: Dict) -> bool:
        """
        Add movie entry
        Expected format:
        {
            "id": "inception",
            "name": "Inception",
            "image": "https://...",
            "genre": ["Sci-Fi", "Thriller"],
            "description": "...",
            "type": "standalone",
            "telegram_link": "t.me/channel/456"
        }
        """
        try:
            required = ['id', 'name', 'type', 'telegram_link']
            if not all(field in movie_data for field in required):
                print(f"❌ Missing required fields: {required}")
                return False
            
            # Convert Telegram link
            converted = self.convert_telegram_link(movie_data['telegram_link'])
            if converted:
                movie_data['video_url'] = converted['embed_url']
                movie_data['video_type'] = converted['type']
            else:
                print(f"⚠️  Could not convert Telegram link for {movie_data['name']}")
            
            movie_data['updated_at'] = datetime.utcnow().isoformat()
            self.movie_data.append(movie_data)
            print(f"✅ Added movie: {movie_data['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding movie: {e}")
            return False
    
    def load_from_json(self, anime_file: str = None, movie_file: str = None):
        """Load existing anime and movie data from JSON files"""
        if anime_file and Path(anime_file).exists():
            with open(anime_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for anime in data.get('anime', []):
                    self.add_anime(anime)
        
        if movie_file and Path(movie_file).exists():
            with open(movie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for movie in data.get('movies', []):
                    self.add_movie(movie)
    
    def save_outputs(self):
        """Save anime and movie JSON files"""
        # Save anime.json
        anime_path = self.output_dir / 'anime.json'
        with open(anime_path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.utcnow().isoformat(),
                'total_anime': len(self.anime_data),
                'anime': self.anime_data
            }, f, indent=2, ensure_ascii=False)
        
        # Save movies.json
        movies_path = self.output_dir / 'movies.json'
        with open(movies_path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.utcnow().isoformat(),
                'total_movies': len(self.movie_data),
                'movies': self.movie_data
            }, f, indent=2, ensure_ascii=False)
        
        # Generate web interface
        self.generate_web_interface()
        
        print(f"\n✅ Saved {len(self.anime_data)} anime and {len(self.movie_data)} movies")
        print(f"📁 Output directory: {self.output_dir.absolute()}")
    
    def generate_web_interface(self):
        """Generate modern web interface for anime and movies"""
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anime & Movies - Video Library</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%);
            color: white;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
        }}
        h1 {{ font-size: 3rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .tab-btn {{
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.3);
            padding: 15px 30px;
            border-radius: 25px;
            color: white;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .tab-btn:hover {{ background: rgba(255,255,255,0.3); transform: translateY(-2px); }}
        .tab-btn.active {{ background: rgba(255,255,255,0.4); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }}
        
        .content {{ display: none; }}
        .content.active {{ display: block; }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 25px;
        }}
        .card {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s;
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255,255,255,0.1);
        }}
        .card:hover {{
            transform: translateY(-10px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.4);
            border-color: rgba(255,255,255,0.3);
        }}
        .card-image {{
            width: 100%;
            height: 350px;
            object-fit: cover;
            background: rgba(0,0,0,0.3);
        }}
        .card-content {{ padding: 15px; }}
        .card-title {{ font-size: 1.2rem; font-weight: bold; margin-bottom: 8px; }}
        .card-genres {{ font-size: 0.85rem; opacity: 0.8; margin-bottom: 10px; }}
        .card-type {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            padding: 20px;
            overflow-y: auto;
        }}
        .modal.active {{ display: block; }}
        .modal-content {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(20px);
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 25px;
        }}
        .modal-title {{ font-size: 2rem; font-weight: bold; }}
        .close-btn {{
            background: rgba(255,0,0,0.8);
            border: none;
            color: white;
            font-size: 1.5rem;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .close-btn:hover {{ background: rgba(255,0,0,1); transform: scale(1.1); }}
        
        .modal-body {{ display: grid; grid-template-columns: 300px 1fr; gap: 30px; }}
        .modal-image {{
            width: 100%;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .modal-info h3 {{ margin-bottom: 15px; font-size: 1.3rem; }}
        .modal-description {{
            line-height: 1.8;
            margin-bottom: 20px;
            opacity: 0.9;
        }}
        
        .episodes-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }}
        .episode-btn {{
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.3);
            color: white;
            padding: 12px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .episode-btn:hover {{
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
        }}
        
        .video-player {{
            width: 100%;
            height: 600px;
            border-radius: 15px;
            margin-top: 20px;
            background: #000;
        }}
        
        @media (max-width: 768px) {{
            .modal-body {{ grid-template-columns: 1fr; }}
            h1 {{ font-size: 2rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎬 Video Library</h1>
            <p>Anime & Movies Collection</p>
        </header>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('anime')">📺 Anime</button>
            <button class="tab-btn" onclick="switchTab('movies')">🎥 Movies</button>
        </div>
        
        <div id="anime" class="content active">
            <div id="animeGrid" class="grid"></div>
        </div>
        
        <div id="movies" class="content">
            <div id="moviesGrid" class="grid"></div>
        </div>
    </div>
    
    <div id="modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle"></div>
                <button class="close-btn" onclick="closeModal()">✕</button>
            </div>
            <div class="modal-body">
                <img id="modalImage" class="modal-image" alt="">
                <div class="modal-info">
                    <h3>📝 Description</h3>
                    <p class="modal-description" id="modalDescription"></p>
                    <div id="episodesSection"></div>
                    <div id="videoSection"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let animeData = [];
        let moviesData = [];
        
        async function loadData() {{
            try {{
                const animeRes = await fetch('anime.json');
                const animeJson = await animeRes.json();
                animeData = animeJson.anime || [];
                
                const moviesRes = await fetch('movies.json');
                const moviesJson = await moviesRes.json();
                moviesData = moviesJson.movies || [];
                
                renderAnime();
                renderMovies();
            }} catch (error) {{
                console.error('Error loading data:', error);
            }}
        }}
        
        function renderAnime() {{
            const grid = document.getElementById('animeGrid');
            grid.innerHTML = animeData.map(anime => `
                <div class="card" onclick='openModal(${{JSON.stringify(anime).replace(/'/g, "&apos;")}}, "anime")'>
                    <img src="${{anime.image || 'https://via.placeholder.com/250x350/667eea/ffffff?text=' + anime.name}}" 
                         class="card-image" alt="${{anime.name}}">
                    <div class="card-content">
                        <div class="card-title">${{anime.name}}</div>
                        <div class="card-genres">${{(anime.genre || []).join(', ')}}</div>
                        <span class="card-type">${{anime.type === 'series' ? '📺 Series' : '🎬 Movie'}}</span>
                    </div>
                </div>
            `).join('');
        }}
        
        function renderMovies() {{
            const grid = document.getElementById('moviesGrid');
            grid.innerHTML = moviesData.map(movie => `
                <div class="card" onclick='openModal(${{JSON.stringify(movie).replace(/'/g, "&apos;")}}, "movie")'>
                    <img src="${{movie.image || 'https://via.placeholder.com/250x350/764ba2/ffffff?text=' + movie.name}}" 
                         class="card-image" alt="${{movie.name}}">
                    <div class="card-content">
                        <div class="card-title">${{movie.name}}</div>
                        <div class="card-genres">${{(movie.genre || []).join(', ')}}</div>
                        <span class="card-type">🎥 Movie</span>
                    </div>
                </div>
            `).join('');
        }}
        
        function switchTab(tab) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tab).classList.add('active');
        }}
        
        function openModal(item, type) {{
            document.getElementById('modalTitle').textContent = item.name;
            document.getElementById('modalImage').src = item.image || '';
            document.getElementById('modalDescription').textContent = item.description || 'No description available.';
            
            const episodesSection = document.getElementById('episodesSection');
            const videoSection = document.getElementById('videoSection');
            
            if (item.type === 'series' && item.episodes) {{
                episodesSection.innerHTML = `
                    <h3>📺 Episodes</h3>
                    <div class="episodes-list">
                        ${{item.episodes.map(ep => `
                            <button class="episode-btn" onclick='playVideo("${{ep.video_url}}")'>
                                EP ${{ep.number}}
                            </button>
                        `).join('')}}
                    </div>
                `;
                videoSection.innerHTML = '<iframe id="videoPlayer" class="video-player" allowfullscreen allow="autoplay"></iframe>';
            }} else if (item.video_url) {{
                episodesSection.innerHTML = '';
                videoSection.innerHTML = `
                    <iframe id="videoPlayer" class="video-player" src="${{item.video_url}}" 
                            allowfullscreen allow="autoplay"></iframe>
                `;
            }}
            
            document.getElementById('modal').classList.add('active');
        }}
        
        function playVideo(url) {{
            document.getElementById('videoPlayer').src = url;
        }}
        
        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
            const player = document.getElementById('videoPlayer');
            if (player) player.src = '';
        }}
        
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
        
        loadData();
    </script>
</body>
</html>'''
        
        html_path = self.output_dir / 'videos.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


# Example usage
if __name__ == '__main__':
    converter = TelegramVideoConverter()
    
    # Example: Add anime series
    converter.add_anime({
        "id": "one-piece",
        "name": "One Piece",
        "image": "https://example.com/one-piece.jpg",
        "genre": ["Action", "Adventure", "Comedy"],
        "description": "Follow Monkey D. Luffy and his pirate crew...",
        "type": "series",
        "episodes": [
            {
                "number": 1,
                "title": "I'm Luffy! The Man Who Will Become Pirate King!",
                "telegram_link": "t.me/animeChannel/1001"
            },
            {
                "number": 2,
                "title": "The Great Swordsman Appears!",
                "telegram_link": "t.me/animeChannel/1002"
            }
        ],
        "related": {
            "previous_season": None,
            "next_season": None
        }
    })
    
    # Example: Add standalone movie
    converter.add_movie({
        "id": "inception",
        "name": "Inception",
        "image": "https://example.com/inception.jpg",
        "genre": ["Sci-Fi", "Thriller", "Action"],
        "description": "A thief who steals corporate secrets through dream-sharing technology...",
        "type": "standalone",
        "telegram_link": "t.me/moviesChannel/5001"
    })
    
    converter.save_outputs()
    print("\n✨ Done! Check public/videos.html")
