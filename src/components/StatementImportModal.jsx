import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Loader2,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  Check,
} from 'lucide-react';
import { importsApi } from '../api/imports';
import { formatINR } from '../utils/formatters';

const IMPORT_TYPES = [
  { id: 'BROKER', label: 'Broker Statement', desc: 'Stocks, ETFs, F&O, trades' },
  { id: 'BANK', label: 'Bank Statement', desc: 'Savings, deposits, debits, credits' },
  { id: 'MUTUAL_FUND', label: 'Mutual Fund (CAS)', desc: 'Folios, NAV, SIPs, redemptions' },
  { id: 'DIGITAL_GOLD', label: 'Digital Gold', desc: 'Grams, buy/sell, vault records' },
  { id: 'DIGITAL_SILVER', label: 'Digital Silver', desc: 'Grams, buy/sell records' },
  { id: 'P2P', label: 'P2P Lending', desc: 'Loans, interest credits, principal' },
  { id: 'GENERIC_PORTFOLIO', label: 'Generic Portfolio', desc: 'Custom assets and transactions' },
];

export default function StatementImportModal({
  isOpen,
  onClose,
  targetPlatform,
  onImportComplete,
}) {
  // Step navigation: 1: UPLOAD, 2: MAPPING, 3: PREVIEW, 4: SUCCESS
  const [step, setStep] = useState(1);

  // Step 1: Upload state
  const [importType, setImportType] = useState('BROKER');
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Step 2 & 3: Import job & preview state
  const [jobId, setJobId] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [activeMapping, setActiveMapping] = useState({});
  const [isUpdatingMapping, setIsUpdatingMapping] = useState(false);

  // Preview filtering & pagination
  const [previewFilter, setPreviewFilter] = useState('ALL'); // 'ALL' | 'ERRORS' | 'WARNINGS' | 'NEW' | 'DUPLICATES'
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 15;

  // Step 4: Commit state
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [commitError, setCommitError] = useState(null);

  // Set default import type based on platform category
  useEffect(() => {
    if (targetPlatform?.category) {
      const cat = targetPlatform.category.toUpperCase();
      if (cat.includes('BANK')) setImportType('BANK');
      else if (cat.includes('MUTUAL_FUND')) setImportType('MUTUAL_FUND');
      else if (cat.includes('GOLD')) setImportType('DIGITAL_GOLD');
      else if (cat.includes('SILVER')) setImportType('DIGITAL_SILVER');
      else if (cat.includes('P2P')) setImportType('P2P');
      else setImportType('BROKER');
    }
  }, [targetPlatform]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    setUploadError(null);
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls', 'pdf'].includes(ext)) {
      setUploadError('Unsupported file type. Please upload a CSV, XLSX, or text-based PDF statement.');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setUploadError('File size exceeds the 15 MB limit.');
      return;
    }
    setSelectedFile(file);
  };

  // Step 1 -> Step 2: Upload and initial parse
  const handleUploadAndParse = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('platform_id', targetPlatform?.id || targetPlatform?.platform_id);
    formData.append('import_type', importType);

    try {
      const data = await importsApi.uploadStatement(formData);
      setJobId(data.id);
      setPreviewData(data);
      setActiveMapping(data.column_mapping || {});
      setStep(2);
    } catch (err) {
      console.error('Upload error:', err);
      setUploadError(err.message || 'Failed to parse statement.');
    } finally {
      setIsUploading(false);
    }
  };

  // Step 2: Update mapping
  const handleMappingChange = (header, targetField) => {
    setActiveMapping((prev) => {
      const next = { ...prev };
      if (!targetField || targetField === 'IGNORE') {
        delete next[header];
      } else {
        next[header] = targetField;
      }
      return next;
    });
  };

  // Apply mapping and move to Step 3 (Preview)
  const handleApplyMappingAndPreview = async () => {
    if (!jobId) return;
    setIsUpdatingMapping(true);
    try {
      const updated = await importsApi.updateMapping(jobId, activeMapping);
      setPreviewData(updated);
      setStep(3);
      setPage(1);
    } catch (err) {
      console.error('Mapping update error:', err);
      setUploadError(err.message || 'Failed to update mapping.');
    } finally {
      setIsUpdatingMapping(false);
    }
  };

  // Step 3 -> Step 4: Commit
  const handleCommit = async () => {
    if (!jobId) return;
    setIsCommitting(true);
    setCommitError(null);

    try {
      const res = await importsApi.commitImport(jobId);
      setCommitResult(res);
      setStep(4);
      if (onImportComplete) {
        onImportComplete(res);
      }
    } catch (err) {
      console.error('Commit error:', err);
      setCommitError(err.message || 'Failed to commit statement to portfolio.');
    } finally {
      setIsCommitting(false);
    }
  };

  const handleResetModal = () => {
    setStep(1);
    setSelectedFile(null);
    setJobId(null);
    setPreviewData(null);
    setActiveMapping({});
    setUploadError(null);
    setCommitError(null);
    setCommitResult(null);
    onClose();
  };

  // Filtered rows for Step 3 table
  const allRows = previewData?.rows || [];
  const filteredRows = useMemo(() => {
    if (previewFilter === 'ERRORS') {
      return allRows.filter((r) => !r.is_valid);
    }
    if (previewFilter === 'WARNINGS') {
      return allRows.filter((r) => r.duplicate_status === 'POSSIBLE_DUPLICATE' || (previewData?.issues || []).some(i => i.row_number === r.row_number && i.severity === 'WARNING'));
    }
    if (previewFilter === 'NEW') {
      return allRows.filter((r) => r.duplicate_status === 'NEW' && r.is_valid);
    }
    if (previewFilter === 'DUPLICATES') {
      return allRows.filter((r) => r.duplicate_status === 'EXACT_DUPLICATE');
    }
    return allRows;
  }, [allRows, previewFilter, previewData?.issues]);

  const totalPages = Math.ceil(filteredRows.length / PAGE_SIZE) || 1;
  const paginatedRows = filteredRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleResetModal}>
      <div
        className="modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-title"
        style={{ maxWidth: step === 3 ? 920 : 680, width: '100%', transition: 'max-width 0.2s ease' }}
      >
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {step > 1 && step < 4 && (
              <button
                type="button"
                className="icon-btn"
                onClick={() => setStep(step - 1)}
                style={{ border: 'none', padding: '4px' }}
                title="Go back"
              >
                <ArrowLeft size={16} />
              </button>
            )}
            <UploadCloud size={20} color="var(--accent-muted, #0284c7)" />
            <div>
              <h2 id="import-title" className="modal-title">
                {step === 4
                  ? 'Import Complete'
                  : targetPlatform
                  ? `Import ${targetPlatform.name} Statement`
                  : 'Import Financial Statement'}
              </h2>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {step === 1 && 'Step 1 of 3: Upload statement file & choose category'}
                {step === 2 && 'Step 2 of 3: Map statement columns to canonical fields'}
                {step === 3 && 'Step 3 of 3: Review parsed records, validation, and duplicates'}
                {step === 4 && 'Data normalized and committed to WealthHub'}
              </div>
            </div>
          </div>
          <button
            className="modal-close-btn"
            onClick={handleResetModal}
            disabled={isUploading || isCommitting}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '78vh', overflowY: 'auto' }}>
          {/* STEP 1: UPLOAD & IMPORT TYPE */}
          {step === 1 && (
            <div>
              {/* Import Type Selector */}
              <div style={{ marginBottom: 18 }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.76rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--text-muted)',
                    marginBottom: 8,
                  }}
                >
                  Statement Category
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 8 }}>
                  {IMPORT_TYPES.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setImportType(t.id)}
                      className="btn-secondary"
                      style={{
                        padding: '8px 10px',
                        textAlign: 'left',
                        borderRadius: 6,
                        borderColor: importType === t.id ? 'var(--text-primary)' : 'var(--border-subtle)',
                        background: importType === t.id ? 'var(--bg-subtle)' : 'transparent',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 2,
                      }}
                    >
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {t.label}
                      </span>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{t.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Dropzone */}
              <div
                className="dropzone-box"
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => document.getElementById('statement-file-input').click()}
                style={{
                  borderColor: dragActive ? 'var(--text-primary)' : 'var(--border-focus)',
                  background: dragActive ? 'var(--bg-surface-hover)' : 'var(--bg-subtle)',
                  padding: '32px 20px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'center',
                  marginBottom: 16,
                }}
              >
                <input
                  type="file"
                  id="statement-file-input"
                  style={{ display: 'none' }}
                  accept=".csv,.xlsx,.xls,.pdf"
                  onChange={handleFileInput}
                  disabled={isUploading}
                />
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
                  <UploadCloud size={36} color="var(--accent-muted, #0284c7)" />
                </div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                  {selectedFile ? selectedFile.name : 'Click to select or drag & drop statement'}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Accepted: CSV, Excel (.xlsx), or text-based PDF (Max 15 MB)
                </div>
              </div>

              {/* Selected File Details */}
              {selectedFile && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: 6,
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-subtle)',
                    marginBottom: 16,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <FileText size={18} color="var(--accent-muted)" />
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{selectedFile.name}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.name.split('.').pop().toUpperCase()}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    title="Remove file"
                  >
                    <X size={14} />
                  </button>
                </div>
              )}

              {uploadError && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: 6,
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: 'var(--negative, #ef4444)',
                    fontSize: '0.82rem',
                    marginBottom: 16,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <AlertCircle size={15} />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
                <button type="button" className="btn-secondary" onClick={handleResetModal} disabled={isUploading}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleUploadAndParse}
                  disabled={!selectedFile || isUploading}
                  style={{ opacity: selectedFile && !isUploading ? 1 : 0.5, display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  {isUploading ? (
                    <>
                      <Loader2 size={14} className="spin-anim" />
                      <span>Parsing Statement...</span>
                    </>
                  ) : (
                    <>
                      <span>Parse & Map Columns</span>
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>
              </div>

              {/* Security guarantee */}
              <div className="security-note" style={{ marginTop: 20 }}>
                <ShieldCheck size={16} />
                <div>
                  <strong>Secure & Ephemeral:</strong> Statement files are processed in memory and deleted immediately. We never store bank passwords or raw statement documents permanently.
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: COLUMN MAPPING */}
          {step === 2 && previewData && (
            <div>
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                  Match Statement Columns to WealthHub
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  We automatically suggested mappings based on your column headers. Please verify or adjust below.
                </div>
              </div>

              <div
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 6,
                  overflow: 'hidden',
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    padding: '8px 14px',
                    background: 'var(--bg-subtle)',
                    borderBottom: '1px solid var(--border-subtle)',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                  }}
                >
                  <div>Statement Column</div>
                  <div>Mapped WealthHub Field</div>
                </div>

                <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                  {(previewData.headers || []).map((header) => {
                    const currentTarget = activeMapping[header] || '';
                    const sampleVal = previewData.rows?.[0]?.[header] || '';

                    return (
                      <div
                        key={header}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          alignItems: 'center',
                          padding: '10px 14px',
                          borderBottom: '1px solid var(--border-subtle)',
                          gap: 12,
                        }}
                      >
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {header}
                          </div>
                          {sampleVal && (
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
                              Sample: {String(sampleVal).slice(0, 35)}
                            </div>
                          )}
                        </div>
                        <div>
                          <select
                            value={currentTarget}
                            onChange={(e) => handleMappingChange(header, e.target.value)}
                            style={{
                              width: '100%',
                              padding: '6px 10px',
                              borderRadius: 6,
                              fontSize: '0.82rem',
                              border: '1px solid var(--border-subtle)',
                              background: 'var(--bg-surface)',
                              color: 'var(--text-primary)',
                            }}
                          >
                            <option value="">-- Ignore Column --</option>
                            {(previewData.available_fields || []).map((f) => (
                              <option key={f.name} value={f.name}>
                                {f.label} {f.required ? '(Required)' : ''}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
                <button type="button" className="btn-secondary" onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleApplyMappingAndPreview}
                  disabled={isUpdatingMapping}
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  {isUpdatingMapping ? (
                    <>
                      <Loader2 size={14} className="spin-anim" />
                      <span>Validating Rows...</span>
                    </>
                  ) : (
                    <>
                      <span>Preview & Validate</span>
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: PREVIEW & VALIDATION */}
          {step === 3 && previewData && (
            <div>
              {/* Summary Cards */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                  gap: 8,
                  marginBottom: 16,
                }}
              >
                <div style={{ padding: '10px', borderRadius: 6, background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Rows</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>{previewData.row_count}</div>
                </div>
                <div style={{ padding: '10px', borderRadius: 6, background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--positive)', textTransform: 'uppercase' }}>Valid Rows</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--positive)' }}>{previewData.valid_row_count}</div>
                </div>
                <div style={{ padding: '10px', borderRadius: 6, background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--accent-muted)', textTransform: 'uppercase' }}>New Records</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-muted)' }}>{previewData.new_count}</div>
                </div>
                <div style={{ padding: '10px', borderRadius: 6, background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Duplicates</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-secondary)' }}>{previewData.duplicate_count}</div>
                </div>
                <div style={{ padding: '10px', borderRadius: 6, background: previewData.warning_count > 0 ? 'rgba(245, 158, 11, 0.08)' : 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.68rem', color: previewData.warning_count > 0 ? '#d97706' : 'var(--text-muted)', textTransform: 'uppercase' }}>Warnings</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: previewData.warning_count > 0 ? '#d97706' : 'var(--text-muted)' }}>{previewData.warning_count}</div>
                </div>
                <div style={{ padding: '10px', borderRadius: 6, background: previewData.error_count > 0 ? 'rgba(239, 68, 68, 0.08)' : 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.68rem', color: previewData.error_count > 0 ? 'var(--negative)' : 'var(--text-muted)', textTransform: 'uppercase' }}>Errors</div>
                  <div style={{ fontSize: '1.15rem', fontWeight: 700, color: previewData.error_count > 0 ? 'var(--negative)' : 'var(--text-muted)' }}>{previewData.error_count}</div>
                </div>
              </div>

              {/* Blocking Error Alert */}
              {previewData.error_count > 0 && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: 6,
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: 'var(--negative)',
                    fontSize: '0.82rem',
                    marginBottom: 14,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <AlertCircle size={16} />
                  <span>
                    <strong>{previewData.error_count} blocking errors found.</strong> Please review invalid rows below or re-check column mapping.
                  </span>
                </div>
              )}

              {/* Table Filter Tabs */}
              <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                {[
                  { id: 'ALL', label: `All (${previewData.row_count})` },
                  { id: 'NEW', label: `New (${previewData.new_count})` },
                  { id: 'DUPLICATES', label: `Duplicates (${previewData.duplicate_count})` },
                  { id: 'WARNINGS', label: `Warnings (${previewData.warning_count})` },
                  { id: 'ERRORS', label: `Errors (${previewData.error_count})` },
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => {
                      setPreviewFilter(f.id);
                      setPage(1);
                    }}
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      borderRadius: 14,
                      border: '1px solid',
                      borderColor: previewFilter === f.id ? 'var(--text-primary)' : 'var(--border-subtle)',
                      background: previewFilter === f.id ? 'var(--text-primary)' : 'transparent',
                      color: previewFilter === f.id ? '#fff' : 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Preview Table */}
              <div
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 6,
                  overflowX: 'auto',
                  marginBottom: 10,
                }}
              >
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '8px 10px', width: 45 }}>#</th>
                      <th style={{ padding: '8px 10px', width: 95 }}>Date</th>
                      <th style={{ padding: '8px 10px', width: 85 }}>Type</th>
                      <th style={{ padding: '8px 10px' }}>Asset / Description</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right', width: 70 }}>Qty</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right', width: 80 }}>Price</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right', width: 95 }}>Amount</th>
                      <th style={{ padding: '8px 10px', width: 95 }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedRows.length === 0 ? (
                      <tr>
                        <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No rows match this filter.
                        </td>
                      </tr>
                    ) : (
                      paginatedRows.map((r) => {
                        const isDup = r.duplicate_status === 'EXACT_DUPLICATE';
                        const isPoss = r.duplicate_status === 'POSSIBLE_DUPLICATE';
                        const isErr = !r.is_valid;

                        return (
                          <tr
                            key={r.row_number}
                            style={{
                              borderBottom: '1px solid var(--border-subtle)',
                              background: isErr
                                ? 'rgba(239, 68, 68, 0.04)'
                                : isDup
                                ? 'var(--bg-subtle)'
                                : 'transparent',
                            }}
                          >
                            <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>{r.row_number}</td>
                            <td style={{ padding: '8px 10px' }}>{r.date || '—'}</td>
                            <td style={{ padding: '8px 10px' }}>
                              <span
                                style={{
                                  fontSize: '0.7rem',
                                  fontWeight: 600,
                                  padding: '2px 6px',
                                  borderRadius: 4,
                                  background: r.transaction_type === 'BUY' || r.transaction_type === 'DEPOSIT'
                                    ? 'rgba(16, 185, 129, 0.1)'
                                    : 'rgba(239, 68, 68, 0.1)',
                                  color: r.transaction_type === 'BUY' || r.transaction_type === 'DEPOSIT'
                                    ? 'var(--positive)'
                                    : 'var(--negative)',
                                }}
                              >
                                {r.transaction_type}
                              </span>
                            </td>
                            <td style={{ padding: '8px 10px' }}>
                              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.asset_name || r.symbol || '—'}</div>
                              {r.description && (
                                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 220 }}>
                                  {r.description}
                                </div>
                              )}
                            </td>
                            <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                              {r.quantity !== null && r.quantity !== undefined ? r.quantity : '—'}
                            </td>
                            <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                              {r.price ? formatINR(r.price) : '—'}
                            </td>
                            <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>
                              {formatINR(r.amount)}
                            </td>
                            <td style={{ padding: '8px 10px' }}>
                              {isErr ? (
                                <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--negative)', display: 'flex', alignItems: 'center', gap: 3 }}>
                                  <AlertCircle size={12} /> Error
                                </span>
                              ) : isDup ? (
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 3 }}>
                                  <RotateCcw size={11} /> Duplicate
                                </span>
                              ) : isPoss ? (
                                <span style={{ fontSize: '0.7rem', color: '#d97706', display: 'flex', alignItems: 'center', gap: 3 }}>
                                  <AlertTriangle size={12} /> Warning
                                </span>
                              ) : (
                                <span style={{ fontSize: '0.7rem', color: 'var(--positive)', display: 'flex', alignItems: 'center', gap: 3 }}>
                                  <Check size={12} /> New
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 16 }}>
                  <div>
                    Page {page} of {totalPages} ({filteredRows.length} rows)
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {commitError && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: 6,
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: 'var(--negative)',
                    fontSize: '0.82rem',
                    marginBottom: 14,
                  }}
                >
                  {commitError}
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14 }}>
                <button type="button" className="btn-secondary" onClick={() => setStep(2)}>
                  Edit Column Mapping
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleCommit}
                  disabled={previewData.error_count > 0 || isCommitting || previewData.new_count === 0}
                  style={{
                    opacity: previewData.error_count > 0 || isCommitting || previewData.new_count === 0 ? 0.5 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  {isCommitting ? (
                    <>
                      <Loader2 size={14} className="spin-anim" />
                      <span>Committing to Portfolio...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={14} />
                      <span>Confirm & Import ({previewData.new_count} records)</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: SUCCESS STATE */}
          {step === 4 && commitResult && (
            <div style={{ textAlign: 'center', padding: '24px 16px' }}>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.1)',
                  color: 'var(--positive)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                }}
              >
                <CheckCircle2 size={32} />
              </div>

              <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                Statement Successfully Imported
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: 420, margin: '0 auto 20px', lineHeight: 1.5 }}>
                Financial records have been safely normalized, idempotently stored, and integrated into your WealthHub portfolio calculation engine.
              </p>

              {/* Results Breakdown */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: 12,
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 8,
                  padding: '16px',
                  marginBottom: 24,
                  textAlign: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--positive)' }}>
                    {commitResult.committed_transactions}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    New Transactions
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                    {commitResult.skipped_duplicates}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Duplicates Skipped
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-muted)' }}>
                    {commitResult.assets_processed}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Assets Updated
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', gap: 10 }}>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleResetModal}
                  style={{ padding: '8px 24px' }}
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
