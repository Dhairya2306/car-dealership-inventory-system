export interface User {
  id: string;
  name: string | null;
  email: string;
  role: "user" | "admin";
  created_at: string;
  updated_at: string;
}

export interface VehicleDetails {
  make: string;
  model: string;
  category: string;
  price: string;
}
export interface Vehicle extends VehicleDetails {
  id: string;
  quantity: number;
  created_at: string;
  updated_at: string;
}
export interface VehiclePage {
  items: Vehicle[];
  total: number;
  limit: number;
  offset: number;
}
export interface Filters {
  make: string;
  model: string;
  category: string;
  min_price: string;
  max_price: string;
}
export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}
