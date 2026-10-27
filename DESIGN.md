# Design

## Existing visual system

Use University of Idaho gold for actions and emphasis, dark ink for text, and
warm light surfaces. Preserve Public Sans for interface text and IBM Plex Mono
for poster numbers. These are already configured in frontend/src/index.css.

## Poster lookup

Attendees stand in a brightly lit ballroom using a phone with one hand while
setting up their poster. Use a light surface, a labeled full-width search input,
and a vertically divided list. Give each row a prominent monospace poster number,
full presenter name, wrapping title, institution, and location when assigned.

Retain the existing logo. Use restrained gold accents and familiar rounded
controls, with visible focus rings. Avoid decorative gradients, nested cards,
and truncation of names or titles. Keep touch targets at least 44 pixels tall.

## States

Show a loading skeleton, an unpublished-directory message, a no-results message
with a clear-search action, and an error message with retry. Distinguish an
unassigned board from a poster number. Printed output should omit controls.
