import React from 'react';
import { Link } from 'react-router-dom';

const ToolCard = ({ id, icon, title, description }) => {
  return (
    <Link to={`/${id}`} className="tool-card">
      <div className="tool-icon">{icon}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-[0.85rem] text-text-muted leading-[1.4]">{description}</p>
    </Link>
  );
};

export default ToolCard;
