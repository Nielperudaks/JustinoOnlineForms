export function requestHasUnapprovedApprover(request) {
  const approvals = request?.approvals || [];
  return approvals.length > 0 && approvals.some((approval) => approval.status !== "approved");
}

export function canRequestBeCancelled(request, currentUser) {
  if (!request || !currentUser) return false;
  if (currentUser.id !== request.requester_id) return false;
  if (["cancelled", "rejected", "approved"].includes(request.status)) return false;

  return requestHasUnapprovedApprover(request);
}

export function getCancellationReasonError(reason) {
  return reason.trim() ? "" : "Cancellation reason is required";
}
