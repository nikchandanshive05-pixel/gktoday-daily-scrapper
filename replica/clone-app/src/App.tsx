import React, { useState, useRef, useEffect } from 'react';
import { 
  Heart, 
  MessageCircle, 
  Share2, 
  Disc, 
  Plus, 
  Check, 
  Volume2, 
  VolumeX, 
  Play, 
  X, 
  Send, 
  Compass, 
  Home, 
  Bell, 
  User, 
  Bookmark,
  Music2
} from 'lucide-react';
import { SEED_VIDEOS, INITIAL_COMMENTS, VideoItem, CommentItem } from './data';

export default function App() {
  const [videos, setVideos] = useState<VideoItem[]>(SEED_VIDEOS);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const [isPlaying, setIsPlaying] = useState(true);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<CommentItem[]>(INITIAL_COMMENTS);
  const [commentInput, setCommentInput] = useState('');
  const [activeTab, setActiveTab] = useState<'foryou' | 'following'>('foryou');
  const [showHeartBurst, setShowHeartBurst] = useState(false);
  const [heartCoords, setHeartCoords] = useState<{ x: number; y: number } | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const currentVideo = videos[currentIndex];

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      if (isPlaying) {
        videoRef.current.play().catch(() => setIsPlaying(false));
      }
    }
  }, [currentIndex]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleDoubleTap = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setHeartCoords({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setShowHeartBurst(true);
    setTimeout(() => setShowHeartBurst(false), 800);

    if (!currentVideo.isLiked) {
      toggleLike();
    }
  };

  const toggleLike = () => {
    setVideos(prev =>
      prev.map((v, i) =>
        i === currentIndex
          ? {
              ...v,
              isLiked: !v.isLiked,
              likesCount: v.isLiked ? v.likesCount - 1 : v.likesCount + 1,
            }
          : v
      )
    );
  };

  const toggleFollow = (e: React.MouseEvent) => {
    e.stopPropagation();
    setVideos(prev =>
      prev.map((v, i) =>
        i === currentIndex
          ? {
              ...v,
              creator: { ...v.creator, isFollowed: !v.creator.isFollowed }
            }
          : v
      )
    );
  };

  const toggleSave = () => {
    setVideos(prev =>
      prev.map((v, i) =>
        i === currentIndex
          ? { ...v, isSaved: !v.isSaved }
          : v
      )
    );
  };

  const handleNextVideo = () => {
    if (currentIndex < videos.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setIsPlaying(true);
    }
  };

  const handlePrevVideo = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      setIsPlaying(true);
    }
  };

  const handlePostComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentInput.trim()) return;

    const newComment: CommentItem = {
      id: `c-${Date.now()}`,
      author: 'you_creator',
      avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80',
      text: commentInput.trim(),
      timestamp: 'Just now',
      likes: 0,
      isLiked: false,
    };

    setComments(prev => [newComment, ...prev]);
    setCommentInput('');
    setVideos(prev =>
      prev.map((v, i) =>
        i === currentIndex ? { ...v, commentsCount: v.commentsCount + 1 } : v
      )
    );
  };

  return (
    <div className="relative w-full h-[100dvh] max-w-md mx-auto bg-black overflow-hidden flex flex-col shadow-2xl">
      {/* Top Header Tabs */}
      <header className="absolute top-0 inset-x-0 h-16 z-30 flex items-center justify-between px-4 bg-gradient-to-b from-black/80 to-transparent">
        <div className="w-10"></div>
        <div className="flex items-center gap-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab('following')}
            className={`transition-colors ${
              activeTab === 'following' ? 'text-white border-b-2 border-white pb-1' : 'text-text-muted hover:text-white'
            }`}
          >
            Following
          </button>
          <button
            onClick={() => setActiveTab('foryou')}
            className={`transition-colors ${
              activeTab === 'foryou' ? 'text-white border-b-2 border-white pb-1' : 'text-text-muted hover:text-white'
            }`}
          >
            For You
          </button>
        </div>
        <button
          onClick={() => setIsMuted(prev => !prev)}
          className="p-2 rounded-full bg-black/40 backdrop-blur-md text-white border border-white/10 active:scale-95 transition-transform"
          aria-label={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5 text-accent" />}
        </button>
      </header>

      {/* Main Video Viewport Layer */}
      <div 
        className="relative flex-1 w-full bg-black cursor-pointer select-none overflow-hidden"
        onClick={togglePlay}
        onDoubleClick={handleDoubleTap}
      >
        <video
          ref={videoRef}
          src={currentVideo.videoUrl}
          loop
          muted={isMuted}
          playsInline
          autoPlay
          className="w-full h-full object-cover"
        />

        {/* Big Center Pause Icon */}
        {!isPlaying && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 pointer-events-none transition-opacity">
            <div className="p-4 rounded-full bg-black/60 text-white/90 backdrop-blur-md transform scale-110 animate-pulse">
              <Play className="w-12 h-12 fill-white" />
            </div>
          </div>
        )}

        {/* Double-Tap Floating Heart Burst */}
        {showHeartBurst && heartCoords && (
          <div
            className="absolute pointer-events-none transform -translate-x-1/2 -translate-y-1/2 animate-ping"
            style={{ left: heartCoords.x, top: heartCoords.y }}
          >
            <Heart className="w-24 h-24 text-danger fill-danger drop-shadow-lg" />
          </div>
        )}

        {/* Bottom-Left Creator & Caption Overlay */}
        <div className="absolute bottom-20 left-3 right-16 z-20 pointer-events-none text-left">
          <div className="pointer-events-auto inline-block">
            <h2 className="font-bold text-white text-base drop-shadow-md hover:underline cursor-pointer">
              @{currentVideo.creator.username}
            </h2>
          </div>
          <p className="text-sm text-white/95 mt-1 leading-snug line-clamp-2 drop-shadow pointer-events-auto">
            {currentVideo.caption}
          </p>
          <div className="flex flex-wrap gap-1.5 mt-2 pointer-events-auto">
            {currentVideo.tags.map(tag => (
              <span key={tag} className="text-xs font-medium text-accent hover:underline cursor-pointer">
                {tag}
              </span>
            ))}
          </div>

          {/* Marquee Sound Pill */}
          <div className="flex items-center gap-2 mt-3 text-xs text-white/90 bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-full w-max border border-white/10 pointer-events-auto">
            <Music2 className="w-3.5 h-3.5 animate-pulse text-accent" />
            <span className="font-medium truncate max-w-[200px]">{currentVideo.soundTitle}</span>
          </div>
        </div>

        {/* Right-Hand Action Rail HUD */}
        <aside className="absolute right-2 bottom-20 z-20 flex flex-col items-center gap-4">
          {/* Avatar + Follow Badge */}
          <div className="relative group">
            <img
              src={currentVideo.creator.avatarUrl}
              alt={currentVideo.creator.displayName}
              className="w-12 h-12 rounded-full border-2 border-white object-cover shadow-lg"
            />
            <button
              onClick={toggleFollow}
              className={`absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-5 h-5 rounded-full flex items-center justify-center text-black font-bold shadow-md transition-all ${
                currentVideo.creator.isFollowed ? 'bg-white text-black' : 'bg-accent text-black scale-100 hover:scale-110'
              }`}
            >
              {currentVideo.creator.isFollowed ? (
                <Check className="w-3.5 h-3.5 stroke-[3]" />
              ) : (
                <Plus className="w-3.5 h-3.5 stroke-[3]" />
              )}
            </button>
          </div>

          {/* Like Action */}
          <div className="flex flex-col items-center">
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleLike();
              }}
              className="p-2.5 rounded-full bg-black/30 backdrop-blur-md border border-white/10 active:scale-75 transition-transform"
              aria-label="Like"
            >
              <Heart
                className={`w-7 h-7 transition-colors ${
                  currentVideo.isLiked ? 'text-danger fill-danger scale-110' : 'text-white'
                }`}
              />
            </button>
            <span className="text-xs font-semibold text-white drop-shadow mt-1">
              {(currentVideo.likesCount / 1000).toFixed(1)}k
            </span>
          </div>

          {/* Comment Action */}
          <div className="flex flex-col items-center">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowComments(true);
              }}
              className="p-2.5 rounded-full bg-black/30 backdrop-blur-md border border-white/10 active:scale-75 transition-transform"
              aria-label="Comments"
            >
              <MessageCircle className="w-7 h-7 text-white fill-white/10" />
            </button>
            <span className="text-xs font-semibold text-white drop-shadow mt-1">
              {currentVideo.commentsCount}
            </span>
          </div>

          {/* Bookmark Action */}
          <div className="flex flex-col items-center">
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleSave();
              }}
              className="p-2.5 rounded-full bg-black/30 backdrop-blur-md border border-white/10 active:scale-75 transition-transform"
              aria-label="Save"
            >
              <Bookmark
                className={`w-6 h-6 transition-colors ${
                  currentVideo.isSaved ? 'text-warning fill-warning' : 'text-white'
                }`}
              />
            </button>
            <span className="text-xs font-semibold text-white drop-shadow mt-1">Save</span>
          </div>

          {/* Share Action */}
          <div className="flex flex-col items-center">
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigator.clipboard?.writeText(window.location.href);
                alert('Video link copied to clipboard!');
              }}
              className="p-2.5 rounded-full bg-black/30 backdrop-blur-md border border-white/10 active:scale-75 transition-transform"
              aria-label="Share"
            >
              <Share2 className="w-6 h-6 text-white" />
            </button>
            <span className="text-xs font-semibold text-white drop-shadow mt-1">
              {(currentVideo.sharesCount / 1000).toFixed(1)}k
            </span>
          </div>

          {/* Rotating Vinyl Disc */}
          <div className={`mt-2 p-1.5 rounded-full bg-surface border-2 border-border shadow-xl ${isPlaying ? 'animate-spin-slow' : ''}`}>
            <Disc className="w-8 h-8 text-accent" />
          </div>
        </aside>

        {/* Vertical Pager Navigation Buttons */}
        <div className="absolute left-2 top-1/2 -translate-y-1/2 z-20 flex flex-col gap-2">
          {currentIndex > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePrevVideo();
              }}
              className="p-2 rounded-full bg-black/50 text-white border border-white/10 hover:bg-black/80 transition-colors"
              title="Previous Video"
            >
              ▲
            </button>
          )}
          {currentIndex < videos.length - 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleNextVideo();
              }}
              className="p-2 rounded-full bg-black/50 text-white border border-white/10 hover:bg-black/80 transition-colors"
              title="Next Video"
            >
              ▼
            </button>
          )}
        </div>
      </div>

      {/* Slide-Up Comments Drawer */}
      {showComments && (
        <div className="absolute inset-x-0 bottom-0 top-1/3 bg-surface rounded-t-2xl z-40 flex flex-col border-t border-border shadow-2xl animate-in slide-in-from-bottom duration-300">
          <div className="flex items-center justify-between p-4 border-b border-border">
            <span className="text-sm font-semibold text-white">
              {comments.length} comments
            </span>
            <button
              onClick={() => setShowComments(false)}
              className="p-1 rounded-full text-text-muted hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
            {comments.map(c => (
              <div key={c.id} className="flex gap-3 text-left">
                <img
                  src={c.avatar}
                  alt={c.author}
                  className="w-9 h-9 rounded-full object-cover shrink-0"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-text-muted">@{c.author}</span>
                    <span className="text-[10px] text-text-muted">{c.timestamp}</span>
                  </div>
                  <p className="text-sm text-white/90 mt-0.5">{c.text}</p>
                </div>
                <div className="flex flex-col items-center justify-center pl-2">
                  <Heart className="w-4 h-4 text-text-muted hover:text-danger cursor-pointer" />
                  <span className="text-[10px] text-text-muted mt-0.5">{c.likes}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Comment Input Footer */}
          <form onSubmit={handlePostComment} className="p-3 border-t border-border bg-surface-elevated flex items-center gap-2">
            <input
              type="text"
              value={commentInput}
              onChange={(e) => setCommentInput(e.target.value)}
              placeholder="Add thoughtful comment..."
              className="flex-1 bg-surface border border-border-input rounded-full px-4 py-2 text-sm text-white focus:outline-none focus:border-accent placeholder:text-text-muted"
            />
            <button
              type="submit"
              disabled={!commentInput.trim()}
              className="p-2 rounded-full bg-accent text-black font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}

      {/* Global 5-Tab Navigation Bar */}
      <nav className="h-16 bg-black border-t border-border flex items-center justify-around px-2 z-30 shrink-0">
        <button className="flex flex-col items-center gap-1 text-white">
          <Home className="w-5 h-5 stroke-[2.5]" />
          <span className="text-[10px] font-medium">Home</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-text-muted hover:text-white">
          <Compass className="w-5 h-5" />
          <span className="text-[10px] font-medium">Discover</span>
        </button>
        {/* Special Center Plus Button */}
        <button 
          onClick={() => alert('Camera & Studio Creator: Trigger file picker or record view')}
          className="relative px-3 py-1.5 rounded-xl bg-gradient-to-r from-accent to-pink-500 p-[2px] shadow-lg hover:scale-105 transition-transform"
        >
          <div className="bg-black rounded-[10px] px-3 py-1 flex items-center justify-center">
            <Plus className="w-5 h-5 text-white stroke-[3]" />
          </div>
        </button>
        <button className="flex flex-col items-center gap-1 text-text-muted hover:text-white">
          <Bell className="w-5 h-5" />
          <span className="text-[10px] font-medium">Inbox</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-text-muted hover:text-white">
          <User className="w-5 h-5" />
          <span className="text-[10px] font-medium">Profile</span>
        </button>
      </nav>
    </div>
  );
}
