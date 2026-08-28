/**
 * The membership rung, as a quiet chip.
 *
 * Presentation only. The authoritative value is
 * `pellier.customers.membership`, and that is what a policy decision reads.
 *
 * No rating glyph. A mark here ranks a membership, not a person, so this is a
 * named rung and never a score out of five.
 */

import React from 'react'
import { MEMBERSHIP, type Membership } from '../../data/membership'

interface MembershipRungProps {
  membership: Membership
  /** Optional trailing count, for the book's summary row. */
  count?: number
  /** Show what the rung earns as a title, for the record header. */
  describe?: boolean
}

const MembershipRung: React.FC<MembershipRungProps> = ({
  membership,
  count,
  describe = false,
}) => {
  const detail = MEMBERSHIP[membership]
  return (
    <span
      className="operator-rung"
      data-rung={membership}
      data-testid={`operator-rung-${membership}`}
      title={describe ? detail.earns : undefined}
    >
      {detail.label}
      {count !== undefined ? (
        <span className="operator-rung-count">{count}</span>
      ) : null}
    </span>
  )
}

export default MembershipRung
