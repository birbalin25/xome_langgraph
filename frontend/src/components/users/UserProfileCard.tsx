import { DollarSign, Heart, Mail, MapPin, Phone, Tag } from "lucide-react";
import type { UserProfile } from "../../types";
import { formatPrice } from "../../lib/utils";

interface UserProfileCardProps {
  profile: UserProfile;
}

const SEGMENT_COLORS: Record<string, string> = {
  first_time_buyer: "bg-green-100 text-green-800",
  investor: "bg-purple-100 text-purple-800",
  upgrader: "bg-blue-100 text-blue-800",
  downsizer: "bg-amber-100 text-amber-800",
};

export default function UserProfileCard({ profile }: UserProfileCardProps) {
  const segmentClass =
    SEGMENT_COLORS[profile.user_segment] || "bg-gray-100 text-gray-800";

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {profile.first_name} {profile.last_name}
          </h3>
          <span
            className={`mt-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${segmentClass}`}
          >
            {profile.user_segment?.replace(/_/g, " ")}
          </span>
        </div>
      </div>

      <div className="space-y-1.5 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-gray-400" />
          {profile.email}
        </div>
        {profile.phone && (
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 text-gray-400" />
            {profile.phone}
          </div>
        )}
        <div className="flex items-center gap-2">
          <MapPin className="h-3.5 w-3.5 text-gray-400" />
          {profile.preferred_city}, {profile.preferred_state}
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="h-3.5 w-3.5 text-gray-400" />
          {formatPrice(profile.budget_min)} &ndash;{" "}
          {formatPrice(profile.budget_max)}
        </div>
        <div className="flex items-center gap-2">
          <Heart className="h-3.5 w-3.5 text-gray-400" />
          {profile.preferred_property_type} &middot;{" "}
          {profile.preferred_beds_min}+ beds
        </div>
        <div className="flex items-center gap-2">
          <Tag className="h-3.5 w-3.5 text-gray-400" />
          ID: <span className="font-mono text-xs">{profile.user_id}</span>
        </div>
      </div>
    </div>
  );
}
