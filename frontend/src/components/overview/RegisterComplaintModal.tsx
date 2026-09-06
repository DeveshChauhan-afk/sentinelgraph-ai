import React, { useState, useEffect, useCallback } from 'react';
import {
  X,
  FilePlus2,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';
import { complaintsApi } from '../../api';
import { ApiError } from '../../api/client';
import {
  IncidentCreate,
  IncidentResponse,
  ReporterType,
  IncidentSource,
} from '../../types';
import { Badge } from '../common/Badge';
import { getPriorityBadgeVariant, getStatusBadgeVariant } from '../../lib/utils';

export interface RegisterComplaintModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (createdIncident: IncidentResponse) => void;
  onNavigateToInvestigate?: (entityValue: string) => void;
}

interface ApiErrorState {
  title: string;
  message: string;
  details?: string[];
}

interface ComplaintPreset {
  id: string;
  label: string;
  title: string;
  description: string;
  reporterType: ReporterType;
  source: IncidentSource;
}

const COMPLAINT_PRESETS: ComplaintPreset[] = [
  {
    id: 'digital-arrest',
    label: 'Digital Arrest Scam',
    title: 'Coercive digital arrest impersonating CBI and Mumbai Police',
    description:
      'Victim was placed under a 4-hour digital arrest via Skype video call by an individual claiming to be a CBI officer calling from +919876543210. Scammer alleged that an illegal narcotics parcel registered to victim Aadhaar was intercepted in customs. Under duress, victim transferred emergency clearance funds of Rs 1,50,000 to SBI account 20394857102 via UPI VPA cbi.clearance@sbi.',
    reporterType: 'citizen',
    source: 'web_portal',
  },
  {
    id: 'upi-phishing',
    label: 'UPI QR Phishing',
    title: 'Unauthorized UPI merchant debit via deceptive cashback QR code',
    description:
      'Victim received an automated WhatsApp message offering festival cashback from phone +919988776655. Upon scanning the embedded QR code in GooglePay, an auto-debit of Rs 49,999 was executed to mule UPI account fastcash.settle@ibl. Bank transaction reference TXN99882241.',
    reporterType: 'citizen',
    source: 'web_portal',
  },
  {
    id: 'investment-syndicate',
    label: 'Investment Syndicate',
    title: 'High-yield algorithmic trading investment syndicate fraud',
    description:
      'Victim was recruited into an exclusive VIP Telegram group "Apex Wealth Alpha" by admin using phone +919123456789. Victim transferred initial investment of Rs 2,50,000 to beneficiary Apex Capital Holdings (Account: 40918273645, IFSC: HDFC0001234). Demands for 25% tax clearance fee blocked all fund withdrawals.',
    reporterType: 'cyber_cell',
    source: 'web_portal',
  },
];

export const RegisterComplaintModal: React.FC<RegisterComplaintModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onNavigateToInvestigate,
}) => {
  // Form input states (exact fields from backend IncidentCreate schema)
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [reporterType, setReporterType] = useState<ReporterType>('citizen');
  const [source, setSource] = useState<IncidentSource>('web_portal');
  const [caseReference, setCaseReference] = useState<string>('');

  // UI state
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [apiError, setApiError] = useState<ApiErrorState | null>(null);
  const [submittedIncident, setSubmittedIncident] = useState<IncidentResponse | null>(null);

  // Reset form helper
  const handleResetForm = useCallback(() => {
    setTitle('');
    setDescription('');
    setReporterType('citizen');
    setSource('web_portal');
    setCaseReference('');
    setErrors({});
    setApiError(null);
    setSubmittedIncident(null);
  }, []);

  // Safe close handler
  const handleClose = useCallback(() => {
    if (isSubmitting) return;
    handleResetForm();
    onClose();
  }, [isSubmitting, handleResetForm, onClose]);

  // Keyboard accessibility: Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting && isOpen) {
        handleClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, handleClose]);

  // Client-side validation mirroring backend schema constraints
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      newErrors.title = 'Title is required.';
    } else if (trimmedTitle.length < 5) {
      newErrors.title = 'Title must be at least 5 characters.';
    } else if (trimmedTitle.length > 255) {
      newErrors.title = 'Title cannot exceed 255 characters.';
    }

    const trimmedDesc = description.trim();
    if (!trimmedDesc) {
      newErrors.description = 'Incident description is required.';
    } else if (trimmedDesc.length < 20) {
      newErrors.description = `Description must be at least 20 characters (currently ${trimmedDesc.length}).`;
    }

    const trimmedCaseRef = caseReference.trim();
    if (trimmedCaseRef && trimmedCaseRef.length > 100) {
      newErrors.caseReference = 'Case reference cannot exceed 100 characters.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleApplyPreset = (preset: ComplaintPreset) => {
    setTitle(preset.title);
    setDescription(preset.description);
    setReporterType(preset.reporterType);
    setSource(preset.source);
    setCaseReference(`CR-${Date.now().toString().slice(-6)}`);
    setErrors({});
    setApiError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    const payload: IncidentCreate = {
      title: title.trim(),
      description: description.trim(),
      reporter_type: reporterType,
      source: source,
      case_reference: caseReference.trim() ? caseReference.trim() : null,
    };

    try {
      const createdIncident = await complaintsApi.createComplaint(payload);
      setSubmittedIncident(createdIncident);
      if (onSuccess) {
        onSuccess(createdIncident);
      }
    } catch (err: any) {
      // User-friendly error message resolution without exposing internal stack traces
      let errTitle = 'Registration Error';
      let errMessage = 'An unexpected error occurred while communicating with the server.';
      let errDetails: string[] | undefined = undefined;

      if (err instanceof ApiError) {
        if (err.status === 409) {
          errTitle = 'Duplicate Case Reference';
          errMessage =
            err.data?.message ||
            `Case reference '${caseReference.trim()}' already exists. Please specify a unique reference.`;
        } else if (err.status === 422) {
          errTitle = 'Validation Failed';
          if (Array.isArray(err.data?.detail)) {
            errMessage = 'Please correct the following fields:';
            errDetails = err.data.detail.map((item: any) => {
              const fieldName = Array.isArray(item.loc)
                ? item.loc.filter((part: any) => part !== 'body').join('.')
                : 'Field';
              return `${fieldName}: ${item.msg}`;
            });
          } else if (typeof err.data?.detail === 'string') {
            errMessage = err.data.detail;
          } else {
            errMessage = 'One or more fields failed validation on the server.';
          }
        } else if (err.status === 408) {
          errTitle = 'Request Timeout';
          errMessage =
            'The server took longer than expected to process entity extraction. The complaint record may still have been persisted.';
        } else if (err.status === 0) {
          errTitle = 'Network Connection Error';
          errMessage =
            'Unable to reach the SentinelGraph backend. Please check network connectivity and ensure the API server is running.';
        } else if (err.status >= 500) {
          errTitle = 'Server Processing Error';
          errMessage =
            'The backend service encountered an internal error while processing the complaint. Please try again or check server logs.';
        } else {
          errMessage = err.data?.message || err.message || errMessage;
        }
      } else if (err?.message) {
        errMessage = err.message;
      }

      setApiError({
        title: errTitle,
        message: errMessage,
        details: errDetails,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInvestigateClick = () => {
    if (!submittedIncident) return;
    const targetIdentifier = submittedIncident.case_reference || submittedIncident.id;
    handleClose();
    if (onNavigateToInvestigate) {
      onNavigateToInvestigate(targetIdentifier);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn"
      role="dialog"
      aria-modal="true"
      aria-labelledby="register-complaint-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          handleClose();
        }
      }}
    >
      <div className="relative w-full max-w-2xl bg-sentinel-surface border border-sentinel-border rounded-xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-sentinel-border flex items-center justify-between bg-sentinel-surface">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-950/60 border border-blue-800/50 flex items-center justify-center text-blue-400">
              <FilePlus2 className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="register-complaint-title"
                className="text-base font-bold text-sentinel-text tracking-tight"
              >
                Register Fraud Complaint
              </h2>
              <p className="text-xs text-sentinel-muted mt-0.5">
                Direct intake to PostgreSQL with real-time Graph-RAG entity extraction
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close dialog"
            className="p-1.5 rounded-lg text-sentinel-muted hover:text-sentinel-text hover:bg-sentinel-surfaceHover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="px-6 py-5 overflow-y-auto flex-1 space-y-5 text-xs">
          {submittedIncident ? (
            /* Success View */
            <div className="py-4 space-y-5">
              <div className="p-4 rounded-lg bg-sentinel-risk-greenBg/30 border border-sentinel-risk-greenBorder flex items-start gap-3.5">
                <CheckCircle2 className="w-6 h-6 text-sentinel-risk-green shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h3 className="text-sm font-semibold text-sentinel-text">
                    Complaint Registered Successfully
                  </h3>
                  <p className="text-xs text-sentinel-muted leading-relaxed">
                    The complaint has been persisted to PostgreSQL. Incident entities (phone numbers,
                    UPI VPAs, bank accounts) have been extracted and linked to the Neo4j knowledge
                    graph.
                  </p>
                </div>
              </div>

              {/* Ingested Summary Card */}
              <div className="rounded-lg bg-sentinel-bg border border-sentinel-border p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-sentinel-border">
                  <span className="text-[11px] font-mono text-sentinel-dim uppercase tracking-wider">
                    Incident Identifier
                  </span>
                  <span className="font-mono font-bold text-blue-400 text-xs">
                    {submittedIncident.case_reference || `CASE-${submittedIncident.id.slice(0, 8).toUpperCase()}`}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-[11px] text-sentinel-dim block">Incident UUID</span>
                    <span className="font-mono text-[11px] text-sentinel-muted select-all">
                      {submittedIncident.id}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-sentinel-dim block">Initial Status</span>
                    <div className="mt-0.5">
                      <Badge variant={getStatusBadgeVariant(submittedIncident.status)}>
                        {submittedIncident.status.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-[11px] text-sentinel-dim block">Triage Priority</span>
                    <div className="mt-0.5">
                      <Badge variant={getPriorityBadgeVariant(submittedIncident.priority)}>
                        {submittedIncident.priority}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-[11px] text-sentinel-dim block">Graph Node Anchor</span>
                    <span className="font-mono text-[11px] text-sentinel-muted">
                      {submittedIncident.graph_node_id || `complaint:${submittedIncident.id}`}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-sentinel-border">
                  <span className="text-[11px] text-sentinel-dim block mb-1">Title</span>
                  <div className="text-xs font-medium text-sentinel-text">
                    {submittedIncident.title}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={handleResetForm}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-medium text-sentinel-text bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border rounded-lg transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-sentinel-muted" />
                  <span>Register Another</span>
                </button>

                {onNavigateToInvestigate && (
                  <button
                    type="button"
                    onClick={handleInvestigateClick}
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-sm transition-colors"
                  >
                    <span>Investigate in Workspace</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* Complaint Input Form */
            <form id="register-complaint-form" onSubmit={handleSubmit} className="space-y-4">
              {/* Presets / Demo Templates */}
              <div className="p-3 rounded-lg bg-sentinel-bg/60 border border-sentinel-border space-y-2">
                <div className="flex items-center justify-between text-[11px] text-sentinel-dim">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                    <span className="font-medium text-sentinel-muted">Quick Scenario Presets:</span>
                  </div>
                  <span>Click to autofill sample narrative</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {COMPLAINT_PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => handleApplyPreset(preset)}
                      className="px-2.5 py-1 text-[11px] rounded bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border hover:border-blue-700/50 text-sentinel-text transition-colors disabled:opacity-50"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* API Error Notification */}
              {apiError && (
                <div className="p-3.5 rounded-lg bg-sentinel-risk-redBg/30 border border-sentinel-risk-redBorder text-xs text-sentinel-text space-y-1.5 animate-fadeIn">
                  <div className="flex items-center gap-2 font-semibold text-sentinel-risk-red">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{apiError.title}</span>
                  </div>
                  <p className="text-sentinel-muted pl-6">{apiError.message}</p>
                  {apiError.details && apiError.details.length > 0 && (
                    <ul className="list-disc list-inside pl-6 space-y-0.5 text-sentinel-muted">
                      {apiError.details.map((detail, idx) => (
                        <li key={idx}>{detail}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Title Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="complaint-title" className="font-semibold text-sentinel-text">
                    Complaint Title <span className="text-sentinel-risk-red">*</span>
                  </label>
                  <span className="text-[11px] font-mono text-sentinel-dim">
                    {title.length}/255
                  </span>
                </div>
                <input
                  id="complaint-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="e.g. Unauthorized UPI transfer impersonating customs official"
                  className={`w-full px-3 py-2 rounded-lg bg-sentinel-bg border text-sentinel-text text-xs placeholder:text-sentinel-dim focus:outline-none focus:ring-1 transition-colors ${
                    errors.title
                      ? 'border-sentinel-risk-redBorder focus:border-sentinel-risk-red focus:ring-sentinel-risk-red'
                      : 'border-sentinel-border focus:border-sentinel-accent focus:ring-sentinel-accent'
                  } disabled:opacity-50`}
                />
                {errors.title ? (
                  <p className="text-[11px] text-sentinel-risk-red font-medium">{errors.title}</p>
                ) : (
                  <p className="text-[11px] text-sentinel-dim">
                    Brief synopsis of the incident (5 to 255 characters).
                  </p>
                )}
              </div>

              {/* Description Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="complaint-description" className="font-semibold text-sentinel-text">
                    Incident Narrative & Evidence Details <span className="text-sentinel-risk-red">*</span>
                  </label>
                  <span
                    className={`text-[11px] font-mono ${
                      description.trim().length >= 20 ? 'text-sentinel-dim' : 'text-sentinel-risk-amber'
                    }`}
                  >
                    {description.length} chars (min 20)
                  </span>
                </div>
                <textarea
                  id="complaint-description"
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="Provide detailed incident narrative including phone numbers, UPI VPAs, bank accounts, dates, and amounts. Entity extraction will automatically discover knowledge graph connections."
                  className={`w-full px-3 py-2 rounded-lg bg-sentinel-bg border text-sentinel-text text-xs placeholder:text-sentinel-dim focus:outline-none focus:ring-1 transition-colors ${
                    errors.description
                      ? 'border-sentinel-risk-redBorder focus:border-sentinel-risk-red focus:ring-sentinel-risk-red'
                      : 'border-sentinel-border focus:border-sentinel-accent focus:ring-sentinel-accent'
                  } disabled:opacity-50`}
                />
                {errors.description ? (
                  <p className="text-[11px] text-sentinel-risk-red font-medium">
                    {errors.description}
                  </p>
                ) : (
                  <p className="text-[11px] text-sentinel-dim">
                    Include specific identifiers (+91 phone numbers, UPI handles, account numbers)
                    for AI entity extraction.
                  </p>
                )}
              </div>

              {/* Metadata Row: Reporter Type & Source */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* Reporter Type */}
                <div className="space-y-1.5">
                  <label htmlFor="complaint-reporter" className="font-semibold text-sentinel-text">
                    Reporter Type <span className="text-sentinel-risk-red">*</span>
                  </label>
                  <select
                    id="complaint-reporter"
                    value={reporterType}
                    onChange={(e) => setReporterType(e.target.value as ReporterType)}
                    disabled={isSubmitting}
                    className="w-full px-3 py-2 rounded-lg bg-sentinel-bg border border-sentinel-border text-sentinel-text text-xs focus:outline-none focus:ring-1 focus:border-sentinel-accent focus:ring-sentinel-accent disabled:opacity-50"
                  >
                    <option value="citizen">Citizen (Individual)</option>
                    <option value="police">Law Enforcement / Police</option>
                    <option value="bank">Bank / Financial Institution</option>
                    <option value="cyber_cell">Cyber Crime Cell / 1930</option>
                    <option value="other">Other Agency</option>
                  </select>
                  <p className="text-[11px] text-sentinel-dim">
                    Originating reporting party
                  </p>
                </div>

                {/* Ingestion Source */}
                <div className="space-y-1.5">
                  <label htmlFor="complaint-source" className="font-semibold text-sentinel-text">
                    Ingestion Source <span className="text-sentinel-risk-red">*</span>
                  </label>
                  <select
                    id="complaint-source"
                    value={source}
                    onChange={(e) => setSource(e.target.value as IncidentSource)}
                    disabled={isSubmitting}
                    className="w-full px-3 py-2 rounded-lg bg-sentinel-bg border border-sentinel-border text-sentinel-text text-xs focus:outline-none focus:ring-1 focus:border-sentinel-accent focus:ring-sentinel-accent disabled:opacity-50"
                  >
                    <option value="web_portal">Web Portal</option>
                    <option value="mobile_app">Mobile App</option>
                    <option value="api">API Integration</option>
                    <option value="bulk_import">Bulk Import</option>
                  </select>
                  <p className="text-[11px] text-sentinel-dim">
                    Channel through which report was logged
                  </p>
                </div>
              </div>

              {/* Case Reference (Optional) */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="complaint-caseref" className="font-semibold text-sentinel-text">
                    Case Reference Number <span className="text-sentinel-dim font-normal">(Optional)</span>
                  </label>
                  <span className="text-[11px] font-mono text-sentinel-dim">
                    {caseReference.length}/100
                  </span>
                </div>
                <input
                  id="complaint-caseref"
                  type="text"
                  value={caseReference}
                  onChange={(e) => setCaseReference(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="e.g. CR-2026-0891 or FIR-442-CYBER"
                  className={`w-full px-3 py-2 rounded-lg bg-sentinel-bg border text-sentinel-text text-xs placeholder:text-sentinel-dim focus:outline-none focus:ring-1 transition-colors ${
                    errors.caseReference
                      ? 'border-sentinel-risk-redBorder focus:border-sentinel-risk-red focus:ring-sentinel-risk-red'
                      : 'border-sentinel-border focus:border-sentinel-accent focus:ring-sentinel-accent'
                  } disabled:opacity-50`}
                />
                {errors.caseReference ? (
                  <p className="text-[11px] text-sentinel-risk-red font-medium">
                    {errors.caseReference}
                  </p>
                ) : (
                  <p className="text-[11px] text-sentinel-dim">
                    External tracking or FIR number. Must be unique across incidents if provided.
                  </p>
                )}
              </div>

              {/* Submitting Progress Indicator */}
              {isSubmitting && (
                <div className="p-3.5 rounded-lg bg-blue-950/40 border border-blue-800/40 flex items-center gap-3 animate-pulse">
                  <Loader2 className="w-5 h-5 text-blue-400 animate-spin shrink-0" />
                  <div className="text-xs text-sentinel-text">
                    <span className="font-semibold block">
                      Persisting Incident & Syncing Knowledge Graph...
                    </span>
                    <span className="text-sentinel-dim">
                      Extracting fraud entities via Gemini and mapping relationships in Neo4j.
                    </span>
                  </div>
                </div>
              )}
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-sentinel-border flex items-center justify-between bg-sentinel-bg/50">
          <div className="flex items-center gap-1.5 text-[11px] text-sentinel-dim">
            <ShieldCheck className="w-4 h-4 text-sentinel-accent" />
            <span>POST /api/v1/complaints/</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-3.5 py-1.5 text-xs font-medium text-sentinel-muted hover:text-sentinel-text bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border rounded-lg transition-colors disabled:opacity-50"
            >
              {submittedIncident ? 'Close' : 'Cancel'}
            </button>

            {!submittedIncident && (
              <button
                type="submit"
                form="register-complaint-form"
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <FilePlus2 className="w-3.5 h-3.5" />
                    <span>Register Complaint</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
