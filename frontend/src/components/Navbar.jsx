import React from 'react';
import { Link } from 'react-router-dom';
import Logo from './Logo';
import ThemeToggle from './ThemeToggle';

const Navbar = () => {
  return (
    <nav className="bg-bg/80 backdrop-blur-md border-b border-border px-6 flex items-center justify-between h-16 sticky top-0 z-[1000]">
      <Link to="/" className="no-underline">
        <Logo />
      </Link>
      <ul className="hidden md:flex list-none gap-8">
        <li><Link to="/" className="no-underline text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest">Tools</Link></li>
        <li><Link to="/pdf-analyser" className="no-underline text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest">Analyser</Link></li>
        <li><Link to="/english-font-converter" className="no-underline text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest">Fonts</Link></li>
        <li><Link to="/ocr" className="no-underline text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest">OCR</Link></li>
        <li className="relative group">
          <span className="text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest cursor-pointer">Media ▾</span>
          <ul className="absolute top-full left-0 hidden group-hover:flex flex-col bg-surface border border-border rounded-xl shadow-lg py-2 z-50 min-w-[160px] list-none">
            <li><Link to="/image-converter" className="block px-4 py-2 text-sm text-text-muted hover:text-primary no-underline">🖼️ Image</Link></li>
            <li><Link to="/video-converter" className="block px-4 py-2 text-sm text-text-muted hover:text-primary no-underline">🎬 Video</Link></li>
            <li><Link to="/audio-converter" className="block px-4 py-2 text-sm text-text-muted hover:text-primary no-underline">🎵 Audio</Link></li>
          </ul>
        </li>
      </ul>
      <div className="flex items-center gap-4">
        <ThemeToggle />
        <div className="h-6 w-[1px] bg-border hidden sm:block"></div>
        <button className="hidden sm:block text-text-muted text-[0.9rem] font-bold hover:text-text transition-colors">Login</button>
        <button className="bg-primary text-white py-2 px-5 rounded-xl text-sm font-black hover:bg-primary-hover hover:shadow-glow transition-all active:scale-95">Sign Up</button>
      </div>
    </nav>
  );
};

export default Navbar;
