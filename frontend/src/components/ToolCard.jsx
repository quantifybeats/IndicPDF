import React from 'react';
import { useStore } from '../store';

const ToolCard = ({ id, icon, title, description }) => {
  const setActiveTool = useStore((state) => state.setActiveTool);

  return (
    <a href="javascript:void(0)" className="tool-card" onClick={() => setActiveTool(id)}>
      <div className="tool-icon">{icon}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-[0.85rem] text-text-muted leading-[1.4]">{description}</p>
    </a>
  );
};

export default ToolCard;
