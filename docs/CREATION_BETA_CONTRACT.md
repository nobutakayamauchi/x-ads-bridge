# Creation Beta Contract

The first sellable creation path is deliberately narrow.

## Supported new-ad shape

- Objective: `WEBSITE_CLICKS`
- Goal: `SITE_VISITS` or `LINK_CLICKS`
- Product: `PROMOTED_TWEETS`
- Creative: one or more existing published X Post IDs supplied/confirmed by the Client
- Placements: `ALL_ON_TWITTER`
- Bid strategy: `AUTO`
- Pay by: `IMPRESSION`
- Targeting: explicit X targeting-criteria objects (keyword/location/etc.)
- Budget: explicit daily and total budget

## Safety lifecycle

1. Create campaign **PAUSED**.
2. Create line item **PAUSED**.
3. Add targeting.
4. Associate confirmed Post IDs.
5. Read back all created entities.
6. Show final X-side state to the Client.
7. Activation is a separate approval-hash/execution-key operation.
8. Activation requires both campaign and line item to be PAUSED immediately before execution.
9. Resume campaign, then line item. If line-item resume fails, campaign may be ACTIVE but the line item remains PAUSED, preventing delivery.

## Explicit non-goals for first paid beta

- creating/uploading a new image or video inside X;
- composing a new X Post through the integration;
- Custom Audiences;
- multiple objectives beyond website traffic;
- automatic budget scale-up.

These are post-beta features. Existing published Posts may contain images/video created by the Client before the ad-creation flow.
