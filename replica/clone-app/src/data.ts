export interface VideoItem {
  id: string;
  creator: {
    id: string;
    username: string;
    displayName: string;
    avatarUrl: string;
    isFollowed: boolean;
  };
  videoUrl: string;
  caption: string;
  tags: string[];
  soundTitle: string;
  likesCount: number;
  commentsCount: number;
  sharesCount: number;
  isLiked: boolean;
  isSaved: boolean;
}

export interface CommentItem {
  id: string;
  author: string;
  avatar: string;
  text: string;
  timestamp: string;
  likes: number;
  isLiked: boolean;
}

export const SEED_VIDEOS: VideoItem[] = [
  {
    id: 'vid-1',
    creator: {
      id: 'u-1',
      username: 'cosmic_wanderer',
      displayName: 'Aria Vance',
      avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
      isFollowed: false,
    },
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    caption: 'Chasing the golden hour reflections across the Pacific coast 🌊✨ Have you seen waves like this?',
    tags: ['#goldenhour', '#sunset', '#coastal', '#travelvibes'],
    soundTitle: 'Aria Vance - Ocean Drift Echoes (Original Audio)',
    likesCount: 14280,
    commentsCount: 382,
    sharesCount: 1120,
    isLiked: false,
    isSaved: false,
  },
  {
    id: 'vid-2',
    creator: {
      id: 'u-2',
      username: 'neon_coder',
      displayName: 'Kaelen Dev',
      avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
      isFollowed: true,
    },
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
    caption: 'Clean-room engineering meets full-stack reactivity in 60 seconds 💻⚡ What do you think of this setup?',
    tags: ['#code', '#developer', '#techlife', '#minimalism'],
    soundTitle: 'Synthwave Beats - Midnight Terminal',
    likesCount: 28940,
    commentsCount: 844,
    sharesCount: 3410,
    isLiked: true,
    isSaved: true,
  },
  {
    id: 'vid-3',
    creator: {
      id: 'u-3',
      username: 'urban_culinary',
      displayName: 'Chef Marco',
      avatarUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
      isFollowed: false,
    },
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
    caption: 'Crispy fire-glazed gyoza with artisanal chili sesame crunch 🥟🔥 Savor every crunch.',
    tags: ['#foodie', '#streetfood', '#gyoza', '#cooking'],
    soundTitle: 'Kitchen Sizzle & Lofi Grooves',
    likesCount: 52100,
    commentsCount: 1290,
    sharesCount: 9430,
    isLiked: false,
    isSaved: false,
  }
];

export const INITIAL_COMMENTS: CommentItem[] = [
  {
    id: 'c-1',
    author: 'serena_sky',
    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80',
    text: 'The colors in this shot are absolutely breathtaking! What camera was this filmed on? 🔥',
    timestamp: '2h ago',
    likes: 142,
    isLiked: false,
  },
  {
    id: 'c-2',
    author: 'dev_alex',
    avatar: 'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=100&auto=format&fit=crop&q=80',
    text: 'Watching this on repeat. The audio sync with the wave peak is so satisfying!',
    timestamp: '5h ago',
    likes: 38,
    isLiked: true,
  }
];
