import React from 'react';

const Navbar = () => {
  return (
    <nav className="bg-surface border-b border-border px-6 flex items-center justify-between h-16 sticky top-0 z-[100]">
      <a href="#" className="nav-logo">
        Indic <span className="text-primary">PDF</span>
      </a>
      <ul className="flex list-none gap-6">
        <li><a href="#convert" className="no-underline text-text text-[0.9rem] font-semibold uppercase">Convert PDF</a></li>
        <li><a href="#all" className="no-underline text-text text-[0.9rem] font-semibold uppercase">All Tools</a></li>
      </ul>
      <div className="flex gap-[10px]">
        <button className="bg-none border-none font-bold cursor-pointer">Login</button>
        <button className="bg-primary text-white border-none py-2 px-4 rounded-md font-bold cursor-pointer hover:bg-primary-hover transition-colors">Sign up</button>
      </div>
    </nav>
  );
};

export default Navbar;
