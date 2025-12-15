import React, { useState, useEffect } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Calendar, Clock, Plus, RefreshCw } from 'lucide-react';
import api from '../../utils/api';
import { toast } from 'sonner';
import CreateReservationDialog from './CreateReservationDialog';
import ReservationList from './ReservationList';

const ReservationSection = () => {
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchReservations = async () => {
    try {
      setRefreshing(true);
      const response = await api.get('/api/user/reservations');
      setReservations(response.data);
    } catch (error) {
      console.error('Error fetching reservations:', error);
      toast.error('Failed to load reservations');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchReservations();
  }, []);

  const handleReservationCreated = () => {
    setShowCreateDialog(false);
    fetchReservations();
    toast.success('Reservation created successfully!');
  };

  const handleCancelReservation = async (reservationId) => {
    try {
      await api.delete(`/api/user/reservations/${reservationId}`);
      toast.success('Reservation cancelled successfully');
      fetchReservations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel reservation');
    }
  };

  const activeReservation = reservations.find(
    r => r.status === 'pending' || r.status === 'active'
  );

  return (
    <Card className="p-6 bg-slate-800/50 border-slate-700">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
            <Calendar className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">My Reservations</h2>
            <p className="text-sm text-slate-400">Manage your charger reservations</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={fetchReservations}
            variant="outline"
            size="sm"
            className="text-white border-slate-600 hover:bg-slate-700"
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            onClick={() => setShowCreateDialog(true)}
            size="sm"
            className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
            disabled={!!activeReservation}
          >
            <Plus className="h-4 w-4 mr-2" />
            New Reservation
          </Button>
        </div>
      </div>

      {activeReservation && (
        <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-semibold text-blue-400 mb-1">Active Reservation</p>
              <p className="text-white font-semibold">{activeReservation.charger_name}</p>
              <div className="flex items-center gap-4 mt-2 text-sm text-slate-300">
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {new Date(activeReservation.start_time).toLocaleString()}
                </span>
                <span>→</span>
                <span>{new Date(activeReservation.end_time).toLocaleString()}</span>
              </div>
            </div>
            <Button
              onClick={() => handleCancelReservation(activeReservation.reservation_id)}
              variant="outline"
              size="sm"
              className="text-red-400 border-red-400 hover:bg-red-400/10"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {!activeReservation && (
        <div className="mb-6 p-4 bg-slate-700/30 border border-slate-600 rounded-lg text-center">
          <p className="text-slate-400 text-sm">
            You don't have any active reservations. Create one to reserve a charger.
          </p>
        </div>
      )}

      <ReservationList
        reservations={reservations}
        loading={loading}
        onCancel={handleCancelReservation}
      />

      <CreateReservationDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleReservationCreated}
      />
    </Card>
  );
};

export default ReservationSection;