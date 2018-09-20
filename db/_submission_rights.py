# Role-based rights to submissions

def can_see(self, user):
    return(self.submission_status == 'published' or
        user.is_authenticated and
           #(user.has_role('Admin') or
            user.has_role(self.species) or \
            self.owner == user) or \
            user in self.delegates

def can_edit(self, user):
    return(user.is_authenticated and
            #(user.has_role('Admin') or
             (self.owner == user and self.submission_status == 'draft'))

def can_see_private(self, user):
    return(user.is_authenticated and
            (self.owner == user or user.has_role(self.species) or user in self.delegates))