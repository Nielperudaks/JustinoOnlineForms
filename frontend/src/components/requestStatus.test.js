import { getRequestStatusConfig } from "./requestStatus";

describe("request status badges", () => {
  test("shows fulfilled custodian requests as fulfilled instead of approved", () => {
    const config = getRequestStatusConfig({
      status: "approved",
      custodian: { status: "fulfilled" },
    });

    expect(config.label).toBe("Fulfilled");
  });

  test("shows custodian pending requests as pending fulfillment", () => {
    const config = getRequestStatusConfig({
      status: "pending",
      custodian: { status: "pending" },
    });

    expect(config.label).toBe("Pending Fulfillment");
  });

  test("keeps regular approved requests labelled as completed", () => {
    const config = getRequestStatusConfig({ status: "approved" });

    expect(config.label).toBe("Completed");
  });
});
