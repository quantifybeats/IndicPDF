import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, Type, ArrowLeft, ShieldCheck, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

const MAPS = {
  serif_bold: {
    a:'𝐚',b:'𝐛',c:'𝐜',d:'𝐝',e:'𝐞',f:'𝐟',g:'𝐠',h:'𝐡',i:'𝐢',j:'𝐣',k:'𝐤',l:'𝐥',m:'𝐦',n:'𝐧',o:'𝐨',p:'𝐩',q:'𝐪',r:'𝐫',s:'𝐬',t:'𝐭',u:'𝐮',v:'𝐯',w:'𝐰',x:'𝐱',y:'𝐲',z:'𝐳',
    A:'𝐀',B:'𝐁',C:'𝐂',D:'𝐃',E:'𝐄',F:'𝐅',G:'𝐆',H:'𝐇',I:'𝐈',J:'𝐉',K:'𝐊',L:'𝐋',M:'𝐌',N:'𝐍',O:'𝐎',P:'𝐏',Q:'𝐐',R:'𝐑',S:'𝐒',T:'𝐓',U:'𝐔',V:'𝐕',W:'𝐖',X:'𝐗',Y:'𝐘',Z:'𝐙'
  },
  sans_bold: {
    a:'𝗮',b:'𝗯',c:'𝗰',d:'𝗱',e:'𝗲',f:'𝗳',g:'𝗴',h:'𝗵',i:'𝗶',j:'𝗷',k:'𝗸',l:'𝗹',m:'𝗺',n:'𝗻',o:'𝗼',p:'𝗽',q:'𝗾',r:'𝗿',s:'𝘀',t:'𝘁',u:'𝘂',v:'𝘃',w:'𝘄',x:'𝗅',y:'𝘆',z:'𝘇',
    A:'𝗔',B:'𝗕',C:'𝗖',D:'𝗗',E:'𝗘',F:'𝗙',G:'𝗚',H:'𝗛',I:'𝗜',J:'𝗝',K:'𝗞',L:'𝗟',M:'𝗠',N:'𝗡',O:'𝗢',P:'𝗣',Q:'𝗤',R:'𝗥',S:'𝗦',T:'𝗧',U:'𝗨',V:'𝗩',W:'𝗪',X:'𝗫',Y:'𝗬',Z:'𝗭'
  },
  cursive: {
    a:'𝓪',b:'𝓫',c:'𝓬',d:'𝓭',e:'𝓮',f:'𝓯',g:'𝓰',h:'𝓱',i:'𝓲',j:'𝓳',k:'𝓴',l:'𝓵',m:'𝓶',n:'𝓷',o:'𝓸',p:'𝓹',q:'𝓺',r:'𝓻',s:'𝓼',t:'𝓽',u:'𝓾',v:'𝓿',w:'𝔀',x:'𝔁',y:'𝔂',z:'𝔃',
    A:'𝓐',B:'𝓑',C:'𝓒',D:'𝓓',E:'𝓔',F:'𝓕',G:'𝓖',H:'𝓗',I:'𝓘',J:'𝓙',K:'𝓚',L:'𝓛',M:'𝓜',N:'𝓝',O:'𝓞',P:'𝓟',Q:'𝓠',R:'𝓡',S:'𝓢',T:'𝓣',U:'𝓤',V:'𝓥',W:'𝓦',X:'𝓧',Y:'𝓨',Z:'𝓩'
  },
  fraktur: {
    a:'𝔞',b:'𝔟',c:'𝔠',d:'𝔡',e:'𝔢',f:'𝔣',g:'𝔤',h:'𝔥',i:'𝔦',j:'𝔧',k:'𝔨',l:'𝔩',m:'𝔪',n:'𝔫',o:'𝔬',p:'𝔭',q:'𝔮',r:'𝔯',s:'𝔰',t:'𝔱',u:'𝔲',v:'𝔳',w:'𝔴',x:'𝔵',y:'𝔶',z:'𝔷',
    A:'𝔄',B:'𝔅',C:'ℭ',D:'𝔇',E:'𝔈',F:'𝔉',G:'𝔊',H:'ℌ',I:'ℑ',J:'𝔍',K:'𝔎',L:'𝔏',M:'𝔐',N:'𝔑',O:'𝔒',P:'𝔓',Q:'𝔔',R:'ℜ',S:'𝔖',T:'𝔗',U:'𝔘',V:'𝔙',W:'𝔚',X:'𝔛',Y:'𝔜',Z:'ℨ'
  },
  mono: {
    a:'𝚊',b:'𝚋',c:'𝚌',d:'𝚍',e:'𝚎',f:'𝚏',g:'𝚐',h:'𝚑',i:'𝚒',j:'𝚓',k:'𝚔',l:'𝚕',m:'𝚖',n:'𝚗',o:'𝚘',p:'𝚙',q:'𝚚',r:'𝚛',s:'𝚜',t:'𝚝',u:'𝚞',v:'𝚟',w:'𝚠',x:'𝚡',y:'𝚢',z:'𝚣',
    A:'𝙰',B:'𝙱',C:'𝙲',D:'𝙳',E:'𝙴',F:'𝙵',G:'𝙶',H:'𝙷',I:'𝙸',J:'𝙹',K:'𝙺',L:'𝙻',M:'𝙼',N:'𝙽',O:'𝙾',P:'𝙿',Q:'𝚀',R:'𝚁',S:'𝚂',T:'𝚃',U:'𝚄',V:'𝚅',W:'𝚆',X:'𝚇',Y:'𝚈',Z:'𝚉'
  }
};

const EnglishFontConverter = () => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  const convert = (text, map) => {
    return text.split('').map(char => map[char] || char).join('');
  };

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="container mx-auto px-6 py-12 max-w-[1200px]">
      <div className="mb-10">
        <Link to="/" className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors text-sm font-bold uppercase tracking-wider mb-6">
          <ArrowLeft size={16} /> Back to Tools
        </Link>
        <div className="flex items-start gap-6">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center text-3xl text-primary border border-primary/20 shrink-0">
            𝔄
          </div>
          <div>
            <h1 className="text-3xl font-black mb-2 tracking-tight">English Font Converter</h1>
            <p className="text-text-muted leading-relaxed max-w-[600px]">Transform your English text into stylish Unicode fonts for social media and professional documents instantly.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        {/* Left: Input */}
        <div className="lg:col-span-5">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="workspace-card p-8 sticky top-24"
          >
            <div className="flex items-center justify-between mb-4">
              <label className="text-[11px] font-black text-text-muted uppercase tracking-widest">Your Text</label>
              <span className="text-[10px] text-primary font-bold">LIVE PREVIEW</span>
            </div>
            <textarea
              className="w-full h-[400px] p-5 bg-bg/50 border border-border rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all resize-none text-xl leading-relaxed"
              placeholder="Type or paste your English text here..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <div className="mt-6 pt-6 border-t border-border flex flex-col gap-4 opacity-60">
              <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest">
                <ShieldCheck size={14} className="text-green-500" /> Client-side mapping
              </div>
              <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest">
                <Clock size={14} className="text-primary" /> Instant transformation
              </div>
            </div>
          </motion.div>
        </div>

        {/* Right: Previews */}
        <div className="lg:col-span-7">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-4"
          >
            {Object.entries(MAPS).map(([id, map]) => {
              const convertedText = convert(input || 'Style Preview', map);
              return (
                <div key={id} className="group relative bg-surface border border-border rounded-radius p-6 hover:border-primary/50 transition-all shadow-shadow hover:shadow-shadow-lg flex items-center justify-between gap-6">
                  <div className="flex-grow min-w-0">
                    <span className="text-[10px] font-black uppercase text-text-muted mb-2 block tracking-widest">{id.replace('_', ' ')}</span>
                    <p className="text-2xl break-words pr-4 text-text">{convertedText}</p>
                  </div>
                  <button 
                    onClick={() => handleCopy(convertedText, id)}
                    className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                      copiedId === id ? 'bg-green-500/10 text-green-500' : 'bg-bg border border-border text-text-muted hover:text-primary hover:border-primary'
                    }`}
                  >
                    {copiedId === id ? <Check size={20} /> : <Copy size={20} />}
                  </button>
                </div>
              );
            })}
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default EnglishFontConverter;
