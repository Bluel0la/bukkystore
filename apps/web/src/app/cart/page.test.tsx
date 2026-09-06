import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QuantityInput } from "@/app/cart/page";

describe("QuantityInput", () => {
  it("commits valid quantities on blur and ignores invalid ones", () => {
    const onCommit = vi.fn();
    render(<QuantityInput onCommit={onCommit} productName="Blue Dress" quantity={1} />);

    const input = screen.getByLabelText("Quantity for Blue Dress");
    fireEvent.change(input, { target: { value: "3" } });
    expect(onCommit).not.toHaveBeenCalled();
    fireEvent.blur(input);
    expect(onCommit).toHaveBeenCalledWith(3);
  });

  it("ignores out-of-range and non-numeric drafts", () => {
    const onCommit = vi.fn();
    render(<QuantityInput onCommit={onCommit} productName="Blue Dress" quantity={1} />);

    const input = screen.getByLabelText("Quantity for Blue Dress");
    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.blur(input);
    fireEvent.change(input, { target: { value: "abc" } });
    fireEvent.blur(input);
    expect(onCommit).not.toHaveBeenCalled();
  });
});
