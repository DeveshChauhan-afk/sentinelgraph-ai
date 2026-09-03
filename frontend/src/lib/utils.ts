import { BadgeVariant } from '../components/common/Badge';

/**
 * Utility functions for formatting and styling.
 */

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  } catch {
    return dateString;
  }
}

export function getRiskLevelBadgeVariant(
  level: string | null | undefined
): BadgeVariant {
  if (!level) return 'neutral';
  const upper = level.toUpperCase();
  if (upper === 'HIGH' || upper === 'CRITICAL') return 'danger';
  if (upper === 'MEDIUM') return 'warning';
  if (upper === 'LOW') return 'success';
  return 'neutral';
}

export function getStatusBadgeVariant(
  status: string | null | undefined
): BadgeVariant {
  if (!status) return 'neutral';
  const lower = status.toLowerCase();
  if (lower === 'escalated') return 'danger';
  if (lower === 'under_investigation') return 'warning';
  if (lower === 'new') return 'info';
  if (lower === 'resolved') return 'success';
  return 'neutral';
}

export function getPriorityBadgeVariant(
  priority: string | null | undefined
): BadgeVariant {
  if (!priority) return 'neutral';
  const lower = priority.toLowerCase();
  if (lower === 'critical' || lower === 'high') return 'danger';
  if (lower === 'medium') return 'warning';
  if (lower === 'low') return 'neutral';
  return 'neutral';
}
