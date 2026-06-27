import {
  canRequestBeCancelled,
  canViewCancellationReason,
  getCancellationReasonError,
} from "./requestCancellation";
import { getRequestFieldType, getSafeLinkHref } from "./requestDetailLinks";

describe("request detail link fields", () => {
  test("finds field types from the saved request field snapshot", () => {
    const request = {
      form_fields: [
        { name: "reference_url", type: "link" },
        { name: "purpose", type: "text" },
      ],
    };

    expect(getRequestFieldType(request, "reference_url")).toBe("link");
    expect(getRequestFieldType(request, "purpose")).toBe("text");
    expect(getRequestFieldType(request, "missing")).toBe("");
  });

  test("normalizes safe link URLs for anchor hrefs", () => {
    expect(getSafeLinkHref("example.com/path")).toBe("https://example.com/path");
    expect(getSafeLinkHref("https://example.com/path")).toBe("https://example.com/path");
    expect(getSafeLinkHref("mailto:support@example.com")).toBe("mailto:support@example.com");
    expect(getSafeLinkHref("javascript:alert(1)")).toBe("");
  });
});

describe("request cancellation rules", () => {
  test("allows requester cancellation while any approver has not approved", () => {
    const request = {
      status: "pending",
      requester_id: "requester-1",
      approvals: [
        { status: "approved" },
        { status: "pending" },
      ],
    };

    expect(canRequestBeCancelled(request, { id: "requester-1" })).toBe(true);
  });

  test("blocks cancellation after all approvers have approved", () => {
    const request = {
      status: "pending",
      requester_id: "requester-1",
      approvals: [
        { status: "approved" },
        { status: "approved" },
      ],
    };

    expect(canRequestBeCancelled(request, { id: "requester-1" })).toBe(false);
  });

  test("lets super admin cancel pending requests even after approvals", () => {
    const request = {
      status: "pending",
      requester_id: "requester-1",
      approvals: [
        { status: "approved" },
        { status: "approved" },
      ],
    };

    expect(
      canRequestBeCancelled(request, { id: "admin-1", role: "super_admin" }),
    ).toBe(true);
  });

  test("shows cancellation reason to requester and super admin only", () => {
    const request = {
      requester_id: "requester-1",
      cancellation_reason: "No longer needed",
    };

    expect(
      canViewCancellationReason(request, { id: "requester-1", role: "requestor" }),
    ).toBe(true);
    expect(
      canViewCancellationReason(request, { id: "admin-1", role: "super_admin" }),
    ).toBe(true);
    expect(
      canViewCancellationReason(request, { id: "other-1", role: "approver" }),
    ).toBe(false);
  });

  test("requires a cancellation reason", () => {
    expect(getCancellationReasonError("  ")).toBe("Cancellation reason is required");
    expect(getCancellationReasonError("No longer needed")).toBe("");
  });
});
