import React from 'react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="bg-surface border-b border-border px-6 flex items-center justify-between h-16 sticky top-0 z-[100]">
      <Link to="/" className="nav-logo text-xl font-bold no-underline">
        Indic <span className="text-primary">PDF</span>
      </Link>
      <ul className="hidden md:flex list-none gap-6">
        <li><Link to="/" className="no-underline text-text text-[0.9rem] font-semibold uppercase hover:text-primary transition-colors">Tools</Link></li>
        <li><Link to="/pdf-analyser" className="no-underline text-text text-[0.9rem] font-semibold uppercase hover:text-primary transition-colors">Analyser</Link></li>
        <li><Link to="/english-font-converter" className="no-underline text-text text-[0.9rem] font-semibold uppercase hover:text-primary transition-colors">English Fonts</Link></li>
      </ul>
      <div className="flex gap-[10px]">
        <button className="hidden sm:block bg-none border-none font-bold cursor-pointer hover:text-primary transition-colors">Login</button>
        <button className="bg-primary text-white border-none py-2 px-4 rounded-md font-bold cursor-pointer hover:bg-primary/90 transition-colors">Sign up</button>
      </div>
    </nav>
  );
};

export default Navbar;
