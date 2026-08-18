# Contract: Versioned Risk Policies

## `GET /api/policies`

Preserves existing fields and adds scoring metadata:

```json
{
  "policies": [
    {
      "ruleId": "POL-NEW-SOURCE",
      "title": "New source or location",
      "description": "Adds risk when an established identity uses an unseen source.",
      "enabled": true,
      "category": "context",
      "conditionKey": "new_source_or_location",
      "points": 20,
      "severityFloor": null,
      "policyVersion": "policy-catalog-v1"
    }
  ]
}
```

The API exposes approved rule metadata but never executable condition code.

## `POST /api/policies/{ruleId}/toggle`

Toggles only the selected stable rule ID and returns the updated rule.

**Response 200**: updated policy object.

**Response 404**: rule ID not found.

**Behavior**:

- Toggle changes future policy snapshots/evaluations.
- Historical policy evaluations and risk assessments remain immutable.
- Toggling does not modify points, condition key, floor, or catalog version.

Changing points, floors, condition keys, or catalog membership is a source-controlled Policy Catalog version change, not an API operation in this feature.
