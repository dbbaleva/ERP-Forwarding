from .base import (
    GridView,
    FormView,
)


class Bookings(GridView, FormView):
    def index(self):
        return self.grid_index({
            'title': 'Bookings',
            'description': 'create/edit booking',
        })

    def create(self):
        return self.form_index({
            'title': 'New Booking',
            'description': 'create new booking',
        })

    def update(self):
        return self.form_index({
            'title': 'Update Booking',
            'description': 'edit/revise booking',
        })

    def grid_data(self):
        return {
            'classifications': [
                ('Airfreight', 'fa-users'),
                ('Brokerage', 'fa-users'),
                ('Export', 'fa-users'),
                ('Import', 'fa-users'),
            ],
            'statuses': [
                ('Draft', '#333'),
                ('Confirmed', '#009011'),
                ('Cancelled', '#FF0000'),
            ],
        }
