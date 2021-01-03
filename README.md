# yt-cast

Turn a collection of YouTube links into a podcast. 

Populate config.json like this:

```
{
  "brandon-sanderson": [
    "https://www.youtube.com/watch?v=H4lWbkERlxo&list=PLSH_xM-KC3ZuOZayK68JAAjj5W9ShnFVC",
    "https://www.youtube.com/watch?v=YyaC7NmPsc0&list=PLSH_xM-KC3ZtjKTR2z8rPWxv1pP6bOVzZ",
    "https://www.youtube.com/watch?v=o3V0Zok_kT0&list=PLSH_xM-KC3ZuteHw3G1ZrCDWQrAVgO0ER"
  ]
}
```

Tested URLs include:

* Playlist URLs (like the above)
* Single video URLs
* Channel URLs

Most youtube URLs should work though.