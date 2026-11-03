import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ShieldCheck, AlertTriangle, Salad, Wheat, Sparkles, Filter } from 'lucide-react';

export function MenuAllergenCatalog() {
  const [menuItems, setMenuItems] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [dietaryFilter, setDietaryFilter] = useState('all');
  const [safetyCheckInput, setSafetyCheckInput] = useState('');
  const [safetyAssessment, setSafetyAssessment] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadMenu = async () => {
    try {
      const data = await api.getMenu({
        category: selectedCategory === 'All' ? undefined : selectedCategory,
        is_gluten_free: dietaryFilter === 'gluten_free' ? true : undefined,
        is_vegan: dietaryFilter === 'vegan' ? true : undefined,
        is_nut_free: dietaryFilter === 'nut_free' ? true : undefined
      });
      setMenuItems(data);
    } catch (err) {
      console.error('Failed to load menu:', err);
    }
  };

  useEffect(() => {
    loadMenu();
  }, [selectedCategory, dietaryFilter]);

  const handleSafetyCheck = async (e) => {
    e.preventDefault();
    if (!safetyCheckInput.trim()) return;
    setLoading(true);
    try {
      const result = await api.checkDietarySafety(safetyCheckInput);
      setSafetyAssessment(result);
    } catch (err) {
      console.error('Dietary check failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const categories = ['All', 'Appetizer', 'Main', 'Dessert'];

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl shadow-2xl flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Salad className="w-5 h-5 text-purple-400" />
            <span>Menu & Allergen Safety Knowledgebase</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            SQL ingredients catalog with strict allergen tagging & cross-contamination protection
          </p>
        </div>
      </div>

      {/* Real-time Dietary Safety Analyzer Tool */}
      <div className="bg-slate-950/70 border border-purple-900/40 rounded-2xl p-4 flex flex-col gap-3">
        <div className="flex items-center gap-2 text-xs font-bold text-purple-300 uppercase tracking-wider font-mono">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Interactive Dietary Guardrail Inspector</span>
        </div>
        <form onSubmit={handleSafetyCheck} className="flex gap-2">
          <input
            type="text"
            value={safetyCheckInput}
            onChange={(e) => setSafetyCheckInput(e.target.value)}
            placeholder="Try: 'Severe peanut allergy', 'celiac disease', 'lactose intolerant', 'vegan'..."
            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
          />
          <button
            type="submit"
            disabled={loading || !safetyCheckInput.trim()}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-800 text-white text-xs font-semibold rounded-xl transition-colors"
          >
            {loading ? 'Evaluating...' : 'Verify Menu Safety'}
          </button>
        </form>

        {safetyAssessment && (
          <div className={`p-4 rounded-xl border text-xs flex flex-col gap-2 mt-2 ${
            safetyAssessment.allergy_level === 'SEVERE_ANAPHYLAXIS'
              ? 'bg-rose-950/40 border-rose-800 text-rose-200'
              : 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
          }`}>
            <div className="flex items-center gap-2 font-bold font-mono">
              {safetyAssessment.allergy_level === 'SEVERE_ANAPHYLAXIS' ? (
                <AlertTriangle className="w-4 h-4 text-rose-400" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              )}
              <span>Allergy Level: {safetyAssessment.allergy_level}</span>
              {safetyAssessment.identified_allergens.length > 0 && (
                <span className="px-2 py-0.5 rounded bg-black/40 font-mono text-[10px]">
                  Allergens: {safetyAssessment.identified_allergens.join(', ')}
                </span>
              )}
            </div>

            {safetyAssessment.kitchen_alert_note && (
              <div className="font-semibold text-rose-300 bg-black/30 p-2 rounded-lg font-mono text-[11px]">
                {safetyAssessment.kitchen_alert_note}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-1">
              <div>
                <span className="font-bold text-emerald-400">Safe Dishes ({safetyAssessment.safe_dishes.length}):</span>
                <ul className="list-disc list-inside text-slate-300 mt-1 space-y-0.5 text-[11px]">
                  {safetyAssessment.safe_dishes.slice(0, 4).map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>

              {safetyAssessment.unsafe_dishes.length > 0 && (
                <div>
                  <span className="font-bold text-rose-400">Flagged Unsafe Dishes ({safetyAssessment.unsafe_dishes.length}):</span>
                  <ul className="list-disc list-inside text-rose-300 mt-1 space-y-0.5 text-[11px]">
                    {safetyAssessment.unsafe_dishes.slice(0, 4).map((d, i) => (
                      <li key={i}>{d.dish_name} (contains {d.conflicting_allergens.join(', ')})</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 bg-slate-950/70 border border-slate-800 rounded-xl">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedCategory === cat
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={dietaryFilter}
            onChange={(e) => setDietaryFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-purple-500"
          >
            <option value="all">All Diets</option>
            <option value="gluten_free">Gluten-Free Only</option>
            <option value="vegan">Vegan Only</option>
            <option value="nut_free">Nut-Free Only</option>
          </select>
        </div>
      </div>

      {/* Menu Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {menuItems.map((item) => {
          const allergens = item.allergens && item.allergens !== 'none'
            ? item.allergens.split(',')
            : [];

          return (
            <div
              key={item.id}
              className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between hover:border-slate-700 transition-all shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-purple-400 font-bold">
                      {item.category}
                    </span>
                    <h3 className="font-bold text-slate-100 text-sm mt-0.5">{item.name}</h3>
                  </div>
                  <span className="font-mono font-bold text-slate-100 text-sm">
                    ${parseFloat(item.price).toFixed(2)}
                  </span>
                </div>

                <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                  {item.description}
                </p>

                <div className="mt-2 text-[11px] text-slate-500">
                  <span className="font-semibold text-slate-400">Ingredients:</span> {item.ingredients}
                </div>
              </div>

              {/* Badges */}
              <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap items-center gap-1.5">
                {allergens.length > 0 ? (
                  allergens.map((alg, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/80 border border-amber-700/60 text-amber-300"
                    >
                      Contains {alg.trim()}
                    </span>
                  ))
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/80 border border-emerald-700/60 text-emerald-300">
                    Allergen Free
                  </span>
                )}

                {item.is_gluten_free && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-950/80 border border-blue-700/60 text-blue-300">
                    Gluten-Free
                  </span>
                )}
                {item.is_vegan && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-teal-950/80 border border-teal-700/60 text-teal-300">
                    Vegan
                  </span>
                )}
                {item.is_nut_free && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-950/80 border border-purple-700/60 text-purple-300">
                    Nut-Free
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

