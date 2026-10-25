"use client";

import { useEffect, useRef, useState } from "react";
import {
  Autocomplete,
  Box,
  CircularProgress,
  TextField,
  Typography,
} from "@mui/material";
import LocationOnOutlined from "@mui/icons-material/LocationOnOutlined";
import PublicOutlined from "@mui/icons-material/PublicOutlined";
import type { LocationSuggestion } from "@/lib/location-search";

export default function LocationAutocomplete({
  label,
  value,
  required,
  error = false,
  placeholder,
  citiesOnly = false,
  onChange,
}: {
  label: string;
  value: string;
  required?: boolean;
  error?: boolean;
  placeholder?: string;
  citiesOnly?: boolean;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const highlighted = useRef<LocationSuggestion | null>(null);
  const [result, setResult] = useState<{
    query: string;
    locations: LocationSuggestion[];
    failed: boolean;
  }>({ query: "", locations: [], failed: false });
  const query = value.trim();
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          q: query,
          citiesOnly: String(citiesOnly),
        });
        const response = await fetch(`/api/locations?${params}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Location search unavailable");
        const body = await response.json();
        if (!controller.signal.aborted)
          setResult({ query, locations: body.locations, failed: false });
      } catch {
        if (!controller.signal.aborted)
          setResult({ query, locations: [], failed: true });
      }
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, citiesOnly, open]);
  const loading = open && result.query !== query;
  return (
    <Autocomplete<LocationSuggestion, false, false, true>
      fullWidth
      freeSolo
      autoHighlight
      selectOnFocus={false}
      clearOnBlur={false}
      handleHomeEndKeys
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      options={result.query === query ? result.locations : []}
      filterOptions={(options) => options}
      getOptionLabel={(option) =>
        typeof option === "string" ? option : option.label
      }
      getOptionKey={(option) =>
        typeof option === "string" ? option : option.id
      }
      inputValue={value}
      value={value || null}
      onInputChange={(_, next, reason) => {
        if (reason === "input" || reason === "clear") onChange(next);
      }}
      onChange={(_, next) =>
        onChange(typeof next === "string" ? next : (next?.label ?? ""))
      }
      onHighlightChange={(_, option) => {
        highlighted.current = option;
      }}
      onKeyDown={(event) => {
        // Enter accepts the visible suggestion; Tab still preserves manual input.
        if (
          event.key === "Enter" &&
          open &&
          result.query === query &&
          result.locations.length
        ) {
          event.preventDefault();
          event.defaultMuiPrevented = true;
          const selected =
            result.locations.find(
              (item) => item.id === highlighted.current?.id,
            ) ?? result.locations[0];
          onChange(selected.label);
          setOpen(false);
        }
      }}
      loading={loading}
      loadingText="Finding your place…"
      renderOption={(props, option) => {
        const { key, ...rest } = props;
        return (
          <Box
            component="li"
            key={key}
            {...rest}
            sx={{ gap: 1.5, py: "12px !important" }}
          >
            {option.kind === "city" ? (
              <LocationOnOutlined color="primary" />
            ) : (
              <PublicOutlined color="primary" />
            )}
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {option.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {option.detail}
              </Typography>
            </Box>
          </Box>
        );
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          required={required}
          error={error}
          label={label}
          placeholder={placeholder}
          helperText={
            result.failed && result.query === query
              ? "Suggestions unavailable. You can still enter a location."
              : undefined
          }
          slotProps={{
            ...params.slotProps,
            htmlInput: { ...params.slotProps.htmlInput, maxLength: 255 },
            input: {
              ...params.slotProps.input,
              endAdornment: (
                <>
                  {loading && <CircularProgress color="inherit" size={18} />}
                  {params.slotProps.input.endAdornment}
                </>
              ),
            },
          }}
        />
      )}
    />
  );
}
