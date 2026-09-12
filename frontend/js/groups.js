/**
 * Groups Module
 * Manages group listing, active group state, group creation, member additions, and member removals.
 */

const Groups = {
  currentGroup: null,
  groupsList: [],

  async loadGroups() {
    try {
      const res = await API.get('/groups');
      this.groupsList = res.data || [];
      this.renderGroupSelector();

      if (this.groupsList.length === 0) {
        document.getElementById('noGroupsContainer').style.display = 'flex';
        document.getElementById('groupDashboardContainer').style.display = 'none';
        this.currentGroup = null;
      } else {
        document.getElementById('noGroupsContainer').style.display = 'none';
        document.getElementById('groupDashboardContainer').style.display = 'block';

        // Check if there was a previously selected active group
        const savedGroupId = localStorage.getItem('billsplitter_active_group');
        const exists = this.groupsList.find((g) => g._id === savedGroupId);

        if (savedGroupId && exists) {
          await this.selectGroup(savedGroupId);
        } else {
          await this.selectGroup(this.groupsList[0]._id);
        }
      }
    } catch (error) {
      showToast(error.message || 'Failed to load groups', 'error');
    }
  },

  renderGroupSelector() {
    const select = document.getElementById('groupSelect');
    if (!select) return;

    if (this.groupsList.length === 0) {
      select.innerHTML = '<option value="" disabled selected>No groups found</option>';
      return;
    }

    select.innerHTML = this.groupsList
      .map(
        (g) =>
          `<option value="${g._id}" ${
            this.currentGroup && this.currentGroup._id === g._id ? 'selected' : ''
          }>${g.name} (${g.members.length} members)</option>`
      )
      .join('');
  },

  async selectGroup(groupId) {
    try {
      const res = await API.get(`/groups/${groupId}`);
      this.currentGroup = res.data;
      localStorage.setItem('billsplitter_active_group', groupId);

      this.renderGroupSelector();
      this.renderGroupBanner();

      // Trigger full group dashboard data refresh
      await Dashboard.refreshGroupData(groupId);
    } catch (error) {
      showToast(error.message || 'Error selecting group', 'error');
    }
  },

  renderGroupBanner() {
    if (!this.currentGroup) return;

    const bannerTitle = document.getElementById('bannerGroupName');
    const bannerSub = document.getElementById('bannerGroupSub');
    const membersListEl = document.getElementById('groupMembersList');

    if (bannerTitle) bannerTitle.textContent = this.currentGroup.name;
    if (bannerSub) {
      bannerSub.textContent = `Created by ${this.currentGroup.createdBy.name} • ${this.currentGroup.members.length} Members`;
    }

    const currentUser = Auth.getUser();
    const isCreator = this.currentGroup.createdBy._id === currentUser?._id;

    if (membersListEl) {
      membersListEl.innerHTML = this.currentGroup.members
        .map((m) => {
          const isUserCreator = m._id === this.currentGroup.createdBy._id;
          const isSelf = m._id === currentUser?._id;
          const canRemove = (isCreator && !isUserCreator) || (isSelf && !isUserCreator);

          return `
            <div class="member-chip ${isUserCreator ? 'creator' : ''}">
              <span>${m.name}${isSelf ? ' (You)' : ''}${isUserCreator ? ' ★ Owner' : ''}</span>
              ${
                canRemove
                  ? `<button class="btn-icon btn-sm" style="width: 20px; height: 20px; font-size: 0.75rem; background: rgba(0,0,0,0.2); border: none; color: white;" onclick="Groups.removeMember('${m._id}', '${m.name}')" title="Remove member">&times;</button>`
                  : ''
              }
            </div>
          `;
        })
        .join('');
    }
  },

  async createGroup(name) {
    try {
      const res = await API.post('/groups', { name });
      showToast(`Group "${res.data.name}" created successfully!`, 'success');
      await this.loadGroups();
      await this.selectGroup(res.data._id);
      return res.data;
    } catch (error) {
      showToast(error.message || 'Failed to create group', 'error');
      throw error;
    }
  },

  async addMember(email) {
    if (!this.currentGroup) return;
    try {
      const res = await API.post(`/groups/${this.currentGroup._id}/members`, { email });
      showToast(res.message || 'Member added successfully', 'success');
      this.currentGroup = res.data;
      this.renderGroupBanner();
      await this.loadGroups();
      await Dashboard.refreshGroupData(this.currentGroup._id);
    } catch (error) {
      showToast(error.message || 'Failed to add member', 'error');
      throw error;
    }
  },

  async removeMember(userId, userName) {
    if (!this.currentGroup) return;
    if (!confirm(`Are you sure you want to remove ${userName} from this group?`)) return;

    try {
      const res = await API.delete(`/groups/${this.currentGroup._id}/members/${userId}`);
      showToast(res.message || 'Member removed', 'success');
      this.currentGroup = res.data;
      this.renderGroupBanner();
      await this.loadGroups();
      await Dashboard.refreshGroupData(this.currentGroup._id);
    } catch (error) {
      showToast(error.message || 'Cannot remove member', 'error');
    }
  },

  initListeners() {
    const groupSelect = document.getElementById('groupSelect');
    if (groupSelect) {
      groupSelect.addEventListener('change', (e) => {
        this.selectGroup(e.target.value);
      });
    }

    // Create Group Modals & Buttons
    const openCreateBtn = document.getElementById('openCreateGroupBtn');
    const emptyCreateBtn = document.getElementById('emptyCreateGroupBtn');
    const createModal = document.getElementById('createGroupModal');
    const createForm = document.getElementById('createGroupForm');

    const showCreateModal = () => {
      if (createModal) createModal.classList.add('active');
    };

    if (openCreateBtn) openCreateBtn.addEventListener('click', showCreateModal);
    if (emptyCreateBtn) emptyCreateBtn.addEventListener('click', showCreateModal);

    if (createForm) {
      createForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('newGroupName');
        const submitBtn = document.getElementById('submitCreateGroupBtn');
        try {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Creating...';
          await Groups.createGroup(nameInput.value);
          nameInput.value = '';
          createModal.classList.remove('active');
        } catch {
          // Toast handles error
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Create Group';
        }
      });
    }

    // Add Member Modal & Form
    const openAddMemberBtn = document.getElementById('openAddMemberBtn');
    const addMemberModal = document.getElementById('addMemberModal');
    const addMemberForm = document.getElementById('addMemberForm');

    if (openAddMemberBtn) {
      openAddMemberBtn.addEventListener('click', () => {
        if (!Groups.currentGroup) {
          showToast('Please select or create a group first', 'error');
          return;
        }
        if (addMemberModal) {
          document.getElementById('memberEmail').value = '';
          document.getElementById('addMemberAlert').className = 'alert-box';
          addMemberModal.classList.add('active');
        }
      });
    }

    if (addMemberForm) {
      addMemberForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const emailInput = document.getElementById('memberEmail');
        const submitBtn = document.getElementById('submitAddMemberBtn');
        const alertBox = document.getElementById('addMemberAlert');
        try {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Adding...';
          alertBox.className = 'alert-box';
          await Groups.addMember(emailInput.value);
          addMemberModal.classList.remove('active');
        } catch (err) {
          alertBox.textContent = err.message || 'Failed to add member';
          alertBox.className = 'alert-box error active';
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Add Member';
        }
      });
    }
  },
};
