import React from 'react';
import { Link } from 'react-router-dom';
import Logo from './Logo';

const Navbar = () => {
  return (
    <nav className="bg-bg/80 backdrop-blur-md border-b border-border px-6 flex items-center justify-between h-16 sticky top-0 z-[1000]">
      <Link to="/" className="no-underline">
        <Logo />
      </Link>
      <ul className="hidden md:flex list-none gap-8">
        <li><Link to="/" className="no-underline text-text-muted text-[0.85rem] font-bold uppercase hover:text-primary transition-all tracking-wider">Tools</Link></li>
        <li><Link to="/pdf-analyser" className="no-underline text-text-muted text-[0.85rem] font-bold uppercase hover:text-primary transition-all tracking-wider">Analyser</Link></li>
        <li><Link to="/english-font-converter" className="no-underline text-text-muted text-[0.85rem] font-bold uppercase hover:text-primary transition-all tracking-wider">English Fonts</Link></li>
        <li><a href="#" className="no-underline text-text-muted text-[0.85rem] font-bold uppercase hover:text-primary transition-all tracking-wider">About</a></li>
      </ul>
      <div className="flex items-center gap-4">
        <button className="hidden sm:block text-text-muted text-[0.9rem] font-bold hover:text-text transition-colors">Login</button>
        <button className="bg-primary text-white py-2 px-5 rounded-lg text-sm font-black hover:bg-primary-hover hover:shadow-glow transition-all active:scale-95">Sign Up</button>
      </div>
    </nav>
  );
};

export default Navbar;
