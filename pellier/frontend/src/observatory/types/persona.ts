/**
 * Pellier Observatory — Persona type
 *
 * Represents a mock customer profile used as the demo identity in the Observatory.
 * Selected via Settings surface.
 *
 * Requirements: 16.5
 */

export interface Persona {
  id: string;
  name: string;
  role: string;
  avatarColor: string;
  customerId: string;
  context: string;
  preferences: string[];
}
