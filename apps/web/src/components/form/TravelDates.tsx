"use client";

import { useState } from "react";
import dayjs from "dayjs";
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import CalendarMonthRounded from "@mui/icons-material/CalendarMonthRounded";
import CloseRounded from "@mui/icons-material/CloseRounded";
import EastRounded from "@mui/icons-material/EastRounded";
import { DateCalendar } from "@mui/x-date-pickers/DateCalendar";

export default function TravelDates({
  start,
  end,
  onChange,
}: {
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [today, setToday] = useState<string | null>(null);
  const [active, setActive] = useState<"start" | "end">("start");
  const minimum =
    active === "end" && start
      ? dayjs(start).add(1, "day")
      : today
        ? dayjs(today)
        : undefined;
  const label = start
    ? `${dayjs(start).format("MMM D, YYYY")} ${end ? `— ${dayjs(end).format("MMM D, YYYY")}` : "— select return"}`
    : "Choose your travel dates";
  return (
    <Box>
      <Typography
        component="label"
        variant="body2"
        className="field-label"
        id="travel-dates-label"
      >
        When are you going?
      </Typography>
      <Button
        fullWidth
        variant="outlined"
        className="date-trigger"
        aria-labelledby="travel-dates-label travel-dates-value"
        aria-haspopup="dialog"
        startIcon={<CalendarMonthRounded />}
        endIcon={<EastRounded />}
        onClick={() => {
          setToday(dayjs().format("YYYY-MM-DD"));
          setActive(start && !end ? "end" : "start");
          setOpen(true);
        }}
      >
        <span id="travel-dates-value">{label}</span>
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="xs"
        fullWidth
        aria-labelledby="calendar-title"
      >
        <DialogTitle id="calendar-title" sx={{ pr: 7 }}>
          Make time for a getaway
          <IconButton
            aria-label="Close calendar"
            onClick={() => setOpen(false)}
            sx={{ position: "absolute", right: 12, top: 12 }}
          >
            <CloseRounded />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <Button
              fullWidth
              variant={active === "start" ? "contained" : "outlined"}
              onClick={() => setActive("start")}
            >
              Departure
              <br />
              {start ? dayjs(start).format("MMM D") : "Choose date"}
            </Button>
            <Button
              fullWidth
              disabled={!start}
              variant={active === "end" ? "contained" : "outlined"}
              onClick={() => setActive("end")}
            >
              Return
              <br />
              {end ? dayjs(end).format("MMM D") : "Choose date"}
            </Button>
          </Stack>
          <DateCalendar
            key={active}
            value={
              (active === "start" ? start : end)
                ? dayjs(active === "start" ? start : end)
                : null
            }
            referenceDate={minimum}
            minDate={minimum}
            maxDate={
              active === "end" && start
                ? dayjs(start).add(90, "day")
                : undefined
            }
            onChange={(value) => {
              if (!value?.isValid()) return;
              const next = value.format("YYYY-MM-DD");
              if (active === "start") {
                onChange(
                  next,
                  end &&
                    dayjs(end).isAfter(value, "day") &&
                    dayjs(end).diff(value, "day") <= 90
                    ? end
                    : "",
                );
                setActive("end");
              } else {
                onChange(start, next);
              }
            }}
            sx={{ width: "100%", maxWidth: 340 }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Your dates include travel days. Select departure first, then return.
          </Typography>
          <Stack direction="row" sx={{ justifyContent: "space-between" }}>
            <Button
              onClick={() => {
                onChange("", "");
                setActive("start");
              }}
            >
              Clear dates
            </Button>
            <Button
              variant="contained"
              disabled={!start || !end}
              onClick={() => setOpen(false)}
            >
              Use these dates
            </Button>
          </Stack>
        </DialogContent>
      </Dialog>
    </Box>
  );
}
