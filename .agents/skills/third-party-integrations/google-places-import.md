# Rule: Google Places Import (Unclaimed Listings)

## Import Discipline
* **Flag on Ingest:** Every Provider row created from a Google Places import must be written with `listing_source = 'google_seeded_unclaimed'`, `is_claimed = false`, and a populated `google_place_id` — never insert an imported row as if it were self-registered.
* **No Silent Overwrites:** Once a listing is claimed, subsequent Google Places sync jobs must not overwrite owner-edited fields (name, description, hours) — imported data only backfills empty fields.

## Claim Flow
* **OTP-Against-Public-Record:** The claim flow verifies the claimant's phone/OTP against the public business record before flipping `is_claimed`; a claim must pass the same Verification gate as a self-registered Provider of that type.
