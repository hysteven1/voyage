"use client";

import { createContext, useContext, useState } from "react";
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
import { PickerDay, type PickerDayProps } from "@mui/x-date-pickers/PickerDay";

const RangeContext = createContext({ start: "", end: "" });
function RangeDay(props: PickerDayProps) {
  const { start, end } = useContext(RangeContext);
  const date = props.day.format("YYYY-MM-DD");
  const first = date === start;
  const last = !!end && date === end;
  const inRange = !!start && !!end && date >= start && date <= end;
  const boundary = first || last;
  return (
    <span
      className="calendar-range-cell"
      style={{
        backgroundColor: inRange ? "#e3eee5" : undefined,
        borderRadius: first ? "50% 0 0 50%" : last ? "0 50% 50% 0" : undefined,
      }}
    >
      <PickerDay
        {...props}
        selected={boundary}
        isVisuallySelected={boundary}
        aria-label={props.day.format("MMMM D, YYYY")}
        aria-selected={boundary || inRange}
        aria-description={
          first
            ? "Start date"
            : last
              ? "End date"
              : inRange
                ? "Within your trip"
                : undefined
        }
        sx={{
          "--PickerDay-horizontalMargin": "0px",
          "--PickerDay-size": "40px",
          ...(boundary
            ? {
                "&.Mui-selected, &.Mui-selected.Mui-disabled": {
                  backgroundColor: "primary.main",
                  color: "primary.contrastText",
                  opacity: 1,
                  fontWeight: 700,
                },
              }
            : inRange
              ? {
                  backgroundColor: "transparent",
                  color: "primary.dark",
                  fontWeight: 500,
                  "&:hover, &:focus": { backgroundColor: "#cfe2d3" },
                }
              : {}),
        }}
      />
    </span>
  );
}

export default function TravelDates({
  start,
  end,
  onChange,
  alreadyThere = false,
  error = false,
}: {
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
  alreadyThere?: boolean;
  error?: boolean;
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
    ? `${dayjs(start).format("MMM D, YYYY")} ${end ? `— ${dayjs(end).format("MMM D, YYYY")}` : "— select end date"}`
    : "Choose your travel dates";
  const nights = start && end ? dayjs(end).diff(dayjs(start), "day") : 0;
  return (
    <Box>
      <Typography
        component="label"
        variant="body2"
        className={`field-label ${error ? "field-error" : ""}`}
        id="travel-dates-label"
      >
        When are you going?
      </Typography>
      <Button
        fullWidth
        variant="outlined"
        style={error ? { borderColor: "#b4403d", color: "#b4403d" } : undefined}
        className={`date-trigger ${error ? "field-error" : ""}`}
        aria-invalid={error}
        aria-required="true"
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
        <span
          id="travel-dates-value"
          className={start ? "date-range-accessible-value" : undefined}
        >
          {label}
        </span>
        {start && (
          <span className="date-range-input" aria-hidden="true">
            <span>
              <small>Start date</small>
              <strong>{dayjs(start).format("MMM D, YYYY")}</strong>
            </span>
            <span>
              <small>End date</small>
              <strong>
                {end ? dayjs(end).format("MMM D, YYYY") : "Choose date"}
              </strong>
            </span>
          </span>
        )}
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
              className="calendar-date-tab"
              aria-pressed={active === "start"}
              variant={active === "start" ? "contained" : "outlined"}
              onClick={() => setActive("start")}
            >
              <small>{alreadyThere ? "Trip starts" : "Departure"}</small>
              <strong>
                {start ? dayjs(start).format("MMM D, YYYY") : "Choose date"}
              </strong>
            </Button>
            <Button
              fullWidth
              className="calendar-date-tab"
              aria-pressed={active === "end"}
              disabled={!start}
              variant={active === "end" ? "contained" : "outlined"}
              onClick={() => setActive("end")}
            >
              <small>{alreadyThere ? "Trip ends" : "Return"}</small>
              <strong>
                {end ? dayjs(end).format("MMM D, YYYY") : "Choose date"}
              </strong>
            </Button>
          </Stack>
          <Typography
            variant="body2"
            color="text.secondary"
            aria-live="polite"
            sx={{ mb: 1 }}
          >
            {active === "start"
              ? "Choose your start date."
              : "Choose your end date."}
            {nights > 0 && ` ${nights} nights selected.`}
          </Typography>
          <RangeContext.Provider value={{ start, end }}>
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
              reduceAnimations
              disableHighlightToday
              showDaysOutsideCurrentMonth
              slots={{ day: RangeDay }}
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
                } else onChange(start, next);
              }}
              sx={{ width: "100%", maxWidth: 340 }}
            />
          </RangeContext.Provider>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Dark circles mark the start and end. The shaded days are your trip.
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
