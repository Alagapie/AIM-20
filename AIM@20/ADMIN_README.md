# 🛠️ AIM20/VISION20 Admin Guide

## 👑 Admin Account Setup

### **First Time Setup:**
1. Run the admin creation script:
   ```bash
   python scripts/create_admin_simple.py
   ```

2. This creates admin user **ABC** with password **123456**

### **Admin Login:**
- Go to the landing page (`/`)
- Click "Admin Access" button at the bottom of the hero section
- Login with:
  - **Username:** `ABC`
  - **Password:** `123456`

---

## 🔧 Admin Features

### **Admin Dashboard (`/admin/`):**
- 📊 System statistics (total users, tasks, goals, sessions)
- 👥 User management overview
- 🔧 Maintenance tools (data cleanup, database backup)
- 📈 Real-time analytics

### **User Management (`/admin/users`):**
- 👀 View all registered users
- 🔍 Search users by username/email
- 📊 User activity statistics
- 👑 Promote/demote admin privileges
- 🗑️ Delete users (with cascade delete)
- 📈 Detailed user profiles and activity history

### **System Management:**
- 🗃️ Database maintenance and cleanup
- 📊 System health monitoring
- 🔄 Data backup functionality
- 📈 User registration analytics

---

## 🔑 Admin Capabilities

### **User Administration:**
- ✅ View all user accounts and details
- ✅ Promote regular users to admin status
- ✅ Remove admin privileges
- ✅ Delete user accounts and all associated data
- ✅ Monitor user activity and statistics

### **System Oversight:**
- ✅ View system-wide statistics
- ✅ Monitor database health
- ✅ Clean up old/invalid data
- ✅ Access system maintenance tools

### **Data Management:**
- ✅ Complete user data deletion (cascade)
- ✅ System cleanup and optimization
- ✅ Database backup and recovery

---

## 🚨 Security Notes

### **Admin Access Control:**
- Only users with `is_admin = True` can access admin routes
- Admin privileges are stored in database (`user.is_admin` field)
- Admins cannot accidentally demote themselves
- All admin actions are protected by authentication

### **Data Safety:**
- User deletion cascades to all related data
- Admin actions are logged for audit trails
- Database backups preserve system integrity

---

## 🎯 Quick Admin Commands

### **Create Admin User:**
```bash
python scripts/create_admin_simple.py
```

### **List All Users:**
```bash
python scripts/make_admin.py list
```

### **Promote User to Admin:**
```bash
python scripts/make_admin.py <username>
```

---

## 📊 Admin Dashboard Features

### **Statistics Overview:**
- Total registered users
- Active users (last 24 hours)
- Total tasks completed
- Total study goals achieved
- Pomodoro sessions logged
- System uptime and health

### **User Analytics:**
- Registration trends
- Most active users
- Feature usage statistics
- User retention metrics

### **Maintenance Tools:**
- Database cleanup (old data removal)
- System health checks
- Backup creation
- Performance monitoring

---

## 🎨 Admin Interface

### **Navigation:**
- Admin panel accessible via `/admin/` or navigation link
- Clean, professional interface matching main app design
- Responsive design for mobile/tablet access

### **User Management Table:**
- Sortable columns (username, registration date, last activity)
- Search functionality
- Bulk actions support
- Detailed user profiles with activity history

### **Action Buttons:**
- **View:** Detailed user information and statistics
- **Make Admin/Remove Admin:** Toggle admin privileges
- **Delete:** Remove user with confirmation modal

---

## 🔍 Troubleshooting

### **Admin Access Issues:**
1. Ensure user is logged in with admin account (ABC/123456)
2. Check that `is_admin` field is set to `True` in database
3. Verify admin routes are accessible at `/admin/`

### **Database Issues:**
1. Run database migration: `python run.py db upgrade`
2. Check database file exists: `instance/aim20_vision20_dev.db`
3. Verify admin column exists in user table

### **Permission Errors:**
1. Confirm admin user has correct credentials
2. Check admin_required decorator is applied to routes
3. Verify database connection is working

---

## 📞 Support

For admin system issues:
1. Check application logs
2. Verify database integrity
3. Test admin login functionality
4. Review user permissions in database

---

## 🎯 Best Practices

### **Admin Usage:**
- Regularly monitor user activity
- Clean up inactive accounts periodically
- Backup database before major changes
- Use admin tools responsibly

### **Security:**
- Change default admin password in production
- Regularly audit admin access logs
- Monitor for suspicious user activity
- Keep admin user list current

---

**Your AIM20/VISION20 admin system is now fully operational! 🚀**