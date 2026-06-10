import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Search, ChevronRight, ChevronDown } from 'lucide-react';

const CATEGORIES = [
  {
    id: 'image',
    label: 'Image',
    formats: ['JPG', 'PNG', 'SVG', 'JPEG', 'TIFF', 'PSD', 'BMP', 'WEBP', 'GIF', 'SGI', 'HDR', 'ICO', 'PDB', 'RGB', 'MAP']
  },
  {
    id: 'document',
    label: 'Document',
    formats: ['DOC', 'DOCX', 'TXT', 'ODT', 'XLS', 'CSV', 'HTML', 'XLSX', 'RTF', 'DJVU', 'DOCM', 'XPS', 'DOTX', 'DOT', 'DBK']
  },
  {
    id: 'ebook',
    label: 'EBook',
    formats: ['PDF', 'EPUB', 'MOBI', 'AZW3', 'FB2', 'LRF', 'LIT']
  },
  {
    id: 'presentation',
    label: 'Presentation',
    formats: ['PPT', 'PPTX', 'ODP', 'PPS', 'PPSX']
  },
  {
    id: 'font',
    label: 'Font',
    formats: ['TTF', 'OTF', 'WOFF', 'WOFF2', 'EOT']
  },
  {
    id: 'vector',
    label: 'Vector',
    formats: ['SVG', 'EPS', 'AI', 'CDR', 'PDF']
  },
  {
    id: 'audio',
    label: 'Audio',
    formats: ['MP3', 'WAV', 'FLAC', 'AAC', 'OGG', 'M4A', 'WMA', 'AMR']
  },
  {
    id: 'video',
    label: 'Video',
    formats: ['MP4', 'AVI', 'MOV', 'MKV', 'WEBM', 'FLV', 'GIF', 'WMV', '3GP']
  }
];

export default function FormatSelector({ formats, value, onChange, disabled }) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('image');
  const [panelStyle, setPanelStyle] = useState({});
  const containerRef = useRef(null);
  const panelRef = useRef(null);

  // Set initial active category based on first supported format
  useEffect(() => {
    if (formats && formats.length > 0) {
      const firstSupported = formats[0].toUpperCase();
      const matchingCategory = CATEGORIES.find(cat => cat.formats.includes(firstSupported));
      if (matchingCategory) setActiveCategory(matchingCategory.id);
    }
  }, [formats]);

  // Calculate fixed position so panel is never clipped by any parent overflow
  const handleOpen = () => {
    if (!isOpen && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const panelWidth = 450;
      const panelHeight = 380;
      const spaceBelow = window.innerHeight - rect.bottom;
      const left = Math.min(rect.right - panelWidth, window.innerWidth - panelWidth - 8);

      if (spaceBelow < panelHeight) {
        // open upward
        setPanelStyle({ position: 'fixed', bottom: window.innerHeight - rect.top + 8, left: Math.max(left, 8), width: panelWidth, zIndex: 9999 });
      } else {
        setPanelStyle({ position: 'fixed', top: rect.bottom + 8, left: Math.max(left, 8), width: panelWidth, zIndex: 9999 });
      }
    }
    setIsOpen(prev => !prev);
  };

  // Close on outside click or scroll
  useEffect(() => {
    if (!isOpen) return;
    const close = (e) => {
      const inTrigger = containerRef.current?.contains(e.target);
      const inPanel = panelRef.current?.contains(e.target);
      if (!inTrigger && !inPanel) setIsOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('scroll', () => setIsOpen(false), { passive: true, capture: true });
    return () => {
      document.removeEventListener('mousedown', close);
    };
  }, [isOpen]);

  // Search filter logic
  const getFilteredFormats = () => {
    if (!searchQuery) {
      const cat = CATEGORIES.find(c => c.id === activeCategory);
      return cat ? cat.formats : [];
    }

    const matches = [];
    CATEGORIES.forEach(cat => {
      cat.formats.forEach(fmt => {
        if (fmt.toLowerCase().includes(searchQuery.toLowerCase()) && !matches.includes(fmt)) {
          matches.push(fmt);
        }
      });
    });
    return matches;
  };

  const filteredFormats = getFilteredFormats();

  const handleSelectFormat = (fmt) => {
    onChange(fmt.toLowerCase());
    setIsOpen(false);
    setSearchQuery('');
  };

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={handleOpen}
        className="bg-white border border-gray-300 hover:border-primary hover:text-primary rounded-lg px-4 py-2 text-sm font-bold text-gray-700 flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span className="uppercase">{value ? value : '...'}</span>
        <ChevronDown size={14} className="text-gray-400 group-hover:text-primary" />
      </button>

      {/* Popover Dropdown Panel — portalled to body to escape all overflow clipping */}
      {isOpen && createPortal(
        <div ref={panelRef} style={panelStyle} className="bg-[#1E1E1E] border border-zinc-800 rounded-xl shadow-2xl p-4 text-white flex flex-col">
          
          {/* Search Input */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#2D2D2D] text-sm text-white placeholder-zinc-500 rounded-lg py-2 pl-9 pr-3 outline-none border-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="border-b border-zinc-800 mb-3" />

          {/* Dual-Pane Layout */}
          <div className="flex gap-2 min-h-[220px]">
            {/* Left Column: Categories List */}
            {!searchQuery && (
              <div className="w-[135px] border-r border-zinc-800 pr-2 flex flex-col gap-1">
                {CATEGORIES.map((cat) => {
                  const isActive = cat.id === activeCategory;
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onMouseEnter={() => setActiveCategory(cat.id)}
                      onClick={() => setActiveCategory(cat.id)}
                      className={`flex items-center justify-between text-[11px] font-black uppercase tracking-wider py-2 px-2.5 rounded-md cursor-pointer text-left transition-colors ${
                        isActive
                          ? 'bg-zinc-800 text-white'
                          : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                      }`}
                    >
                      <span>{cat.label}</span>
                      {isActive && <ChevronRight size={12} className="text-primary" />}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Right Column: Formats Grid */}
            <div className="flex-1 pl-2 max-h-[260px] overflow-y-auto">
              <h5 className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-3">
                {searchQuery ? 'Search Results' : CATEGORIES.find(c => c.id === activeCategory)?.label}
              </h5>

              {filteredFormats.length === 0 ? (
                <div className="text-center py-8 text-zinc-500 text-xs font-bold">
                  No formats found.
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-1.5">
                  {filteredFormats.map((fmt) => {
                    const isSelected = value && value.toUpperCase() === fmt;
                    return (
                      <button
                        key={fmt}
                        type="button"
                        onClick={() => handleSelectFormat(fmt)}
                        className={`text-xs font-black py-2.5 px-3 rounded-md text-center transition-all uppercase cursor-pointer border-none ${
                          isSelected
                            ? 'bg-primary text-white'
                            : 'bg-[#2D2D2D] hover:bg-primary text-zinc-200 hover:text-white'
                        }`}
                        title={`Convert to ${fmt}`}
                      >
                        {fmt}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      , document.body)}
    </div>
  );
}
