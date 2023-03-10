# eBay to Discord WebHook bot

Bot that scrapes searches of eBay, saving and notifying a Discord WebHook based on configured notification settings.

## Running

There are only three ways to run the script:

- Normally, with no arguments
- Passing in the argument `debug`
  - Rune normally, except fetched pages are saved to files for later debugging errors
- Passin in the argument `test-webhook`
  - Sends test notifications with sample data

## Config

The `config.json` is broken into three sections:

- `ebay`
- `searches`
- `discord`

### `ebay`

- `request_timeout`
  - How long to wait - in seconds - for a request to return data before failing in an error
  - It's not safe to make requests to proxies without setting a timeout, as it would leave the bot hanging forever if the proxy fails
- `minimum_interval`
  - Minimum number of seconds to wait before looping through all data

### `searches`

This is an array of search objects:

- `query`
  - The actual search query to execute
- `seconds_interval`
  - How often in seconds to execute the search
- `price_min`
  - Minimum price filter
- `price_max`
  - Maximum price filter
- `listing_type`
  - [Type of listing](#types) to request
- `sort_by`
  - [Sorting method](#types) to request
- `page_length`
  - [Number of listings per page](#types) to request
- `top_n_listings`
  - The top N listings to notify for, what is at the top depends on your chosen sorting method.

### `discord`

- `webhook_url`
  - The WebHook URL you receive when creation
- `seconds_delay`
  - Number of seconds to ensure between notifications
- `first_run_silence`
  - Number of seconds to remain silent during the first run
- `notifications`
  - List of notification objects

### Notification objects

A Notification object represents a message to be sent to the WebHook.

- `id`
  - Required, it MUST be unique amount all notifications AND a string
  - Changing this will mess with the caching, resulting in duplicate notifications
- `minutes_before`
  - Optional, if included, it means this notification will only apply to listings that have at *minimum* `minutes_before` before they end
  - If a listing is found with only five minutes left, and there is a notification object with `minutes_before` set to `10`, it will send the notification
- `type`
  - Optional, [type of listing](#types) this notification is for
  - If omitted, defaults to `ALL`
- `message`
  - Shorthand convenient way to set `json.content`
  - Unlike `json.content`, accepts a list of strings, with each string being a new line
  - Supports [all variables](#variables)
- `json`
  - Raw JSON to send - see the [Official API](https://discordapp.com/developers/docs/resources/webhook#execute-webhook) for usage details.
  - Additional, there are various [Embed Visualizers](https://leovoel.github.io/embed-visualizer/) that allow easy generation of this code
  - All string-values have [variable](#variables) replacement applied to them, no matter how nested or what their keys are

## Types

There are various keys that only accept a subset of valid types - strings are case sensitive:

- Listing:
  - `ALL`
  - `AUCTION`
  - `BUY`
- Sorting:
  - `ENDING`
  - `CHEEPEST`
  - `PRICIEST`
  - `NEAREST`
  - `NEWEST`
  - `BEST MATCH`
  - `CHEEPEST_TOTAL`
  - `PRICIEST_TOTAL`
- Page lengths:
  - 25
  - 50
  - 100
  - 200

## Variables

These are the values from the listing you may use when creating messages:

```json
{
  "id": "string id",
  "listing_id": "listing id",
  "image_url": "https image url",
  "url": "https listing url",
  "title": "item title",
  "misc_details": ["condition", "etc"],
  "type": "AUCTION",
  "ending": 1568560937, # Second the listing ends, available on some BUY listings
  "curr_price": 15.50,
  "prev_price": null,
  "shipping_price": 0,
  "seller": {
    "username": "my_un",
    "review_count": 198062,
    "positive_percentage": 99.5,
    "store_url": "http://stores.ebay.co.uk/MyStoreUrl",
    "name": "My Username"
  }
}
```

These attributes may be None:

- `prev_price`
- `seller.store_url`
- `seller.name`

There are also three additional usable values:

- `ending_datetime`
  - It's the value of the `ending` property in listing, but in a human-readable format.
- `ending_12h`
  - A `HH:MM A/PM` format of the `ending` property.
- `now_12h`
  - The current time, in `HH:MM A/PM` format.

***

If you enter something that doesn't exist, it will replaced by the text `INVALID KEY`

All the direct attributes can be accessed by surrounding them with `{}`s:

```json
{
  "key": "{url}"
}
```

The sub-directory values - in the seller for instance - can be accessed by using the `[]`s:

```json
{
  "key": "{seller[username]}"
}
```
