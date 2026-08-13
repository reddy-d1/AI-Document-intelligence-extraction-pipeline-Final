
import React, { useState } from 'react';
import { AlertTriangle, ShieldCheck, Edit3, Table, Layers } from 'lucide-react';
import { ExtractedFieldItem, ValidationItem } from '../services/api';

interface EditableFieldFormProps {
  fields: ExtractedFieldItem[];
  validationErrors: ValidationItem[];
  onFieldChange: (fieldId: string, newValue: string) => void;
  onFieldSelect?: (box: any) => void;
  onProcessDocument?: () => void;
}

export const EditableFieldForm: React.FC<EditableFieldFormProps> = ({
  fields,
  validationErrors,
  onFieldChange,
  onFieldSelect,
  onProcessDocument,
}) => {
  const [localValues, setLocalValues] = useState<Record<string, string>>({});

  React.useEffect(() => {
    // Reset local edited state when fresh field data arrives from backend
    setLocalValues({});
  }, [fields]);

  const handleInputChange = (fieldId: string, value: string) => {
    setLocalValues((prev) => ({ ...prev, [fieldId]: value }));
    onFieldChange(fieldId, value);
  };

  const getConfidenceBadge = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct >= 90) {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-500/30">
          {pct}% Confident
        </span>
      );
    } else if (pct >= 70) {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950/80 text-amber-400 border border-amber-500/30">
          {pct}% Review
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-950/80 text-red-400 border border-red-500/30">
        {pct}% Low Conf
      </span>
    );
  };

  const findFieldError = (fieldId: string, fieldName: string) => {
    return validationErrors.find(
      (v) => v.field_id === fieldId || v.message.toLowerCase().includes(fieldName.toLowerCase())
    );
  };

  // Group fields into Sections: General / Contact, Primary Entities, Repeatable Lists / Tables, Financials
  const categorizeField = (fieldName: string, dataType: string) => {
    const fn = fieldName.toLowerCase();
    if (dataType === 'json' || fn.includes('items') || fn.includes('education') || fn.includes('experience') || fn.includes('transactions') || fn.includes('projects') || fn.includes('skills')) {
      return 'Structured Arrays & Tables';
    } else if (fn.includes('vendor') || fn.includes('party') || fn.includes('customer') || fn.includes('holder') || fn.includes('name') || fn.includes('patient')) {
      return 'Parties & Contact Info';
    } else if (fn.includes('amount') || fn.includes('tax') || fn.includes('subtotal') || fn.includes('price') || fn.includes('balance')) {
      return 'Financials & Values';
    }
    return 'Document Metadata & Identifiers';
  };

  const groupedFields: Record<string, ExtractedFieldItem[]> = {};
  fields.forEach((f) => {
    const category = categorizeField(f.field_name, f.data_type);
    if (!groupedFields[category]) groupedFields[category] = [];
    groupedFields[category].push(f);
  });

  return (
    <div className="space-y-6">
      {fields.length === 0 ? (
        <div className="text-center py-14 px-4 bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-4">
          <div className="w-12 h-12 rounded-full bg-blue-600/10 text-blue-400 border border-blue-500/20 flex items-center justify-center mx-auto">
            <Edit3 className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-200">No Extracted Fields Yet</p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              This document hasn't been processed yet or is currently queued. Click below to run the AI extraction pipeline.
            </p>
          </div>
          {onProcessDocument && (
            <button
              onClick={onProcessDocument}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-blue-600/20 transition-all"
            >
              <Edit3 className="w-4 h-4" />
              <span>Run Extraction Engine</span>
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedFields).map(([category, catFields]) => (
            <div key={category} className="space-y-3">
              <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
                {category.includes('Arrays') ? (
                  <Table className="w-4 h-4 text-blue-400" />
                ) : (
                  <Layers className="w-4 h-4 text-indigo-400" />
                )}
                <h3 className="text-xs font-bold text-slate-300 tracking-wider uppercase">
                  {category} ({catFields.length})
                </h3>
              </div>

              <div className="space-y-3">
                {catFields.map((field) => {
                  const val = localValues[field.id] !== undefined ? localValues[field.id] : (field.field_value || '');
                  const err = findFieldError(field.id, field.field_name);
                  const isJson = field.data_type === 'json' || field.field_name.includes('items') || val.startsWith('{') || val.startsWith('[');

                  let formattedVal = val;
                  if (isJson) {
                    try {
                      formattedVal = JSON.stringify(JSON.parse(val), null, 2);
                    } catch {
                      formattedVal = val;
                    }
                  }

                  return (
                    <div
                      key={field.id}
                      onClick={() => onFieldSelect && field.bounding_box && onFieldSelect(field.bounding_box)}
                      className={`glass-card p-4 rounded-xl space-y-2 transition-all ${err ? 'border-amber-500/40 bg-amber-950/10' : ''
                        }`}
                    >
                      {/* Field Header */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-slate-200 capitalize">
                            {field.field_name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono uppercase bg-slate-900 px-1.5 py-0.5 rounded">
                            {field.data_type}
                          </span>
                        </div>

                        <div className="flex items-center space-x-2">
                          {field.is_validated && (
                            <span className="flex items-center space-x-1 text-[11px] text-emerald-400 font-medium bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-500/30">
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>Verified</span>
                            </span>
                          )}
                          {getConfidenceBadge(field.confidence_score)}
                        </div>
                      </div>

                      {/* Input Field or Prettified JSON Area */}
                      {!isJson ? (
                        <div className="relative">
                          <input
                            type="text"
                            value={val}
                            onChange={(e) => handleInputChange(field.id, e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 font-medium pr-8"
                          />
                          <Edit3 className="w-3.5 h-3.5 text-slate-600 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                        </div>
                      ) : (
                        <textarea
                          rows={Math.min(10, Math.max(4, formattedVal.split('\n').length))}
                          value={formattedVal}
                          onChange={(e) => handleInputChange(field.id, e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500 resize-y"
                        />
                      )}

                      {/* Inline Validation Alert */}
                      {err && (
                        <div className="flex items-start space-x-1.5 text-[11px] text-amber-400 bg-amber-950/40 p-2 rounded border border-amber-500/30">
                          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                          <span>{err.message}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
