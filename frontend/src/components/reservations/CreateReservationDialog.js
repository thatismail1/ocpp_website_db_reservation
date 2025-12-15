import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import api from '../../utils/api';
import { toast } from 'sonner';
import { Calendar, Clock, Zap } from 'lucide-react';

const CreateReservationDialog = ({ open, onClose, onSuccess }) => {
  const [chargers, setChargers] = useState([]);
  const [selectedCharger, setSelectedCharger] = useState('');
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [duration, setDuration] = useState('1');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingChargers, setLoadingChargers] = useState(true);

  useEffect(() => {
    if (open) {
      fetchChargers();
      // Set default date to today
      const today = new Date();
      setStartDate(today.toISOString().split('T')[0]);
      // Set default time to next hour
      const nextHour = new Date(today.getTime() + 60 * 60 * 1000);
      setStartTime(nextHour.toTimeString().slice(0, 5));
    }
  }, [open]);

  const fetchChargers = async () => {
    try {
      setLoadingChargers(true);
      const response = await api.get('/api/user/reservations/availability');
      setChargers(response.data.chargers || []);
    } catch (error) {
      console.error('Error fetching chargers:', error);
      toast.error('Failed to load chargers');
    } finally {
      setLoadingChargers(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedCharger || !startDate || !startTime) {
      toast.error('Please fill in all required fields');
      return;
    }

    const startDateTime = new Date(`${startDate}T${startTime}`);
    const endDateTime = new Date(startDateTime.getTime() + parseInt(duration) * 60 * 60 * 1000);

    try {
      setLoading(true);
      await api.post('/api/user/reservations', {
        charger_id: selectedCharger,
        start_time: startDateTime.toISOString(),
        end_time: endDateTime.toISOString(),
        notes: notes || null,
      });
      onSuccess();
      // Reset form
      setSelectedCharger('');
      setNotes('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create reservation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px] bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white">Create New Reservation</DialogTitle>
          <DialogDescription className="text-slate-400">
            Reserve a charger for a specific time slot
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="charger" className="text-white">
              Select Charger *
            </Label>
            <Select value={selectedCharger} onValueChange={setSelectedCharger}>
              <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                <SelectValue placeholder="Choose a charger" />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                {loadingChargers ? (
                  <SelectItem value="loading" disabled className="text-slate-400">
                    Loading chargers...
                  </SelectItem>
                ) : chargers.length === 0 ? (
                  <SelectItem value="none" disabled className="text-slate-400">
                    No chargers available
                  </SelectItem>
                ) : (
                  chargers.map((charger) => (
                    <SelectItem
                      key={charger.charger_id}
                      value={charger.charger_id}
                      className="text-white hover:bg-slate-600"
                    >
                      <div className="flex items-center justify-between w-full">
                        <span>{charger.charger_name}</span>
                        {charger.available_now && (
                          <span className="ml-2 text-xs text-green-400 flex items-center gap-1">
                            <Zap className="h-3 w-3" />
                            Available
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="date" className="text-white flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Start Date *
              </Label>
              <input
                type="date"
                id="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="time" className="text-white flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Start Time *
              </Label>
              <input
                type="time"
                id="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="duration" className="text-white">
              Duration (hours) *
            </Label>
            <Select value={duration} onValueChange={setDuration}>
              <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                {[0.5, 1, 1.5, 2, 3, 4, 6, 8].map((hrs) => (
                  <SelectItem
                    key={hrs}
                    value={hrs.toString()}
                    className="text-white hover:bg-slate-600"
                  >
                    {hrs} {hrs === 1 ? 'hour' : 'hours'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes" className="text-white">
              Notes (optional)
            </Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any special notes for this reservation..."
              className="bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="text-white border-slate-600 hover:bg-slate-700"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || !selectedCharger}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
            >
              {loading ? 'Creating...' : 'Create Reservation'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CreateReservationDialog;