# GitHub Scraper Plan

## Goal

Build a GitHub scraper that finds GitHub profiles by location, checks whether each GitHub username also exists as a Telegram username, and saves valid contacts to a JSON file.

## Search Input

The scraper should accept a location in this form:

```text
city, state, country
```

The country should default to `United States` when it is not provided.

Examples:

```text
Austin, Texas, United States
Austin, Texas
```

## Data To Fetch

For each matching GitHub profile, only collect:

- GitHub username
- GitHub profile link

No other GitHub profile data is required.

## Telegram Check

For every GitHub username found, check whether a Telegram account exists with the same username.

Example:

```text
GitHub username: btakita
Telegram username to check: btakita
Telegram URL: https://t.me/btakita
```

If the Telegram account does not exist, skip that GitHub profile.

If the Telegram account exists, save the contact.

## Output

Valid contacts should be saved to a JSON file.

Example `contacts.json`:

```json
[
  {
    "githubUsername": "btakita",
    "githubUrl": "https://github.com/btakita",
    "telegramUsername": "btakita",
    "telegramUrl": "https://t.me/btakita"
  }
]
```

## Scraper Flow

1. Accept a location input from the user.
2. Normalize the location.
3. If country is missing, use `United States`.
4. Search GitHub users by location.
5. Extract only the GitHub username and GitHub profile URL.
6. For each GitHub username, check whether the same Telegram username exists.
7. Skip profiles without a matching Telegram account.
8. Add matching profiles to `contacts.json`.
9. Avoid duplicate contacts.

## GitHub Search Strategy

Use GitHub user search with a location query.

Example query:

```text
location:"Austin, Texas, United States"
```

Possible GitHub search URL:

```text
https://github.com/search?q=location%3A%22Austin%2C+Texas%2C+United+States%22&type=users
```

## Telegram Validation Strategy

Check whether the Telegram profile page exists:

```text
https://t.me/{username}
```

The scraper should treat the account as valid only when Telegram indicates that the username exists.

## Important Rules

- Only save contacts where the Telegram username exists.
- Do not save GitHub profiles without Telegram matches.
- Do not save duplicate usernames.
- Keep the output JSON simple and easy to reuse.
- Respect rate limits and avoid aggressive scraping.

## Future Improvements

- Add pagination support for GitHub search results.
- Add retry handling for failed network requests.
- Add configurable output file path.
- Add CLI options for city, state, and country.
- Add logging for skipped profiles and successful matches.
- Add tests for location parsing and duplicate filtering.
