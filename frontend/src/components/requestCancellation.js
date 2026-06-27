import { isSuperAdminRole } from "../lib/roles";

export function requestHasUnapprovedApprover(request) {
  const approvals = request?.approvals || [];
  return approvals.length > 0 && approvals.some((approval) => approval.status !== "approved");
}

export function canRequestBeCancelled(request, currentUser) {
  if (!request || !currentUser) return false;
  if (["cancelled", "rejected", "approved"].includes(request.status)) return false;

  if (isSuperAdminRole(currentUser.role)) return true;
  if (currentUser.id !== request.requester_id) return false;

  return requestHasUnapprovedApprover(request);
}

export function canViewCancellationReason(request, currentUser) {
  if (!request || !currentUser) return false;
  return currentUser.id === request.requester_id || isSuperAdminRole(currentUser.role);
}

export function getCancellationReasonError(reason) {
  return reason.trim() ? "" : "Cancellation reason is required";
}
