import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Calendar, Clock, X, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const getStatusBadge = (status) => {
  const statusConfig = {
    pending: { label: 'Pending', variant: 'default', icon: Clock, className: 'bg-blue-500' },
    active: { label: 'Active', variant: 'default', icon: CheckCircle, className: 'bg-green-500' },
    completed: { label: 'Completed', variant: 'secondary', icon: CheckCircle, className: 'bg-gray-500' },
    cancelled: { label: 'Cancelled', variant: 'destructive', icon: XCircle, className: 'bg-red-500' },
    no_show: { label: 'No Show', variant: 'destructive', icon: AlertCircle, className: 'bg-orange-500' },
  };

  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <Badge className={`${config.className} text-white flex items-center gap-1 w-fit`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
};

const ReservationList = ({ reservations, loading, onCancel }) => {
  if (loading) {
    return (
      <div className="text-center py-8 text-slate-400">
        <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
        Loading reservations...
      </div>
    );
  }

  if (reservations.length === 0) {
    return (
      <div className="text-center py-8">
        <Calendar className="h-12 w-12 text-slate-500 mx-auto mb-3" />
        <p className="text-slate-400">No reservations yet</p>
        <p className="text-sm text-slate-500 mt-1">
          Create your first reservation to get started
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-slate-700">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-700 hover:bg-slate-700/50">
            <TableHead className="text-slate-300">Charger</TableHead>
            <TableHead className="text-slate-300">Start Time</TableHead>
            <TableHead className="text-slate-300">End Time</TableHead>
            <TableHead className="text-slate-300">Status</TableHead>
            <TableHead className="text-slate-300">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {reservations.map((reservation) => (
            <TableRow
              key={reservation.id}
              className="border-slate-700 hover:bg-slate-700/30"
            >
              <TableCell className="text-white font-medium">
                {reservation.charger_name}
                {reservation.notes && (
                  <p className="text-xs text-slate-400 mt-1">{reservation.notes}</p>
                )}
              </TableCell>
              <TableCell className="text-slate-300">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-slate-400" />
                  {new Date(reservation.start_time).toLocaleString()}
                </div>
              </TableCell>
              <TableCell className="text-slate-300">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  {new Date(reservation.end_time).toLocaleString()}
                </div>
              </TableCell>
              <TableCell>{getStatusBadge(reservation.status)}</TableCell>
              <TableCell>
                {(reservation.status === 'pending' || reservation.status === 'active') && (
                  <Button
                    onClick={() => onCancel(reservation.reservation_id)}
                    variant="ghost"
                    size="sm"
                    className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default ReservationList;