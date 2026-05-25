from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, SAFE_METHODS
from django.utils import timezone
from django.db.models import Sum, Count, Q

from .models import (
    User, UserProfile, Course, CourseDetail, ModuleCategory, Module,
    ModuleContent, Assignment, Submission, UserProgress,
    CourseEnrollment, PaymentTransaction, Badge, UserBadge, Leaderboard
)
from .serializers import (
    UserSerializer, RegisterSerializer, CourseListSerializer,
    CourseDetailFullSerializer, ModuleSerializer, ModuleContentSerializer,
    AssignmentSerializer, SubmissionSerializer, SubmissionGradeSerializer,
    UserProgressSerializer, CourseEnrollmentSerializer,
    PaymentTransactionSerializer, BadgeSerializer, UserBadgeSerializer,
    LeaderboardSerializer, DashboardSerializer
)
from .permissions import IsMentorOrAdmin, IsAdminOrReadOnly


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        if request.method == 'PATCH':
            profile = request.user.profile
            for field in ['first_name', 'last_name', 'avatar_url']:
                if field in request.data:
                    setattr(profile, field, request.data[field])
            profile.save()
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailFullSerializer

    def get_queryset(self):
        qs = Course.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(is_published=True)
        if self.action == 'list':
            return qs.prefetch_related('modules', 'created_user__profile')
        return qs.prefetch_related(
            'modules__contents', 'created_user__profile', 'detail'
        )

    def perform_create(self, serializer):
        serializer.save(created_user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        if CourseEnrollment.objects.filter(user=request.user, course=course).exists():
            return Response({'detail': 'Already enrolled'}, status=status.HTTP_400_BAD_REQUEST)
        if course.price > 0:
            return Response({'detail': 'Paid course. Complete payment first.'},
                            status=status.HTTP_402_PAYMENT_REQUIRED)
        enrollment = CourseEnrollment.objects.create(user=request.user, course=course)
        return Response(CourseEnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def leaderboard(self, request, pk=None):
        course = self.get_object()
        entries = Leaderboard.objects.filter(course=course).select_related('user__profile')
        serializer = LeaderboardSerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def assignments(self, request, pk=None):
        course = self.get_object()
        modules = course.modules.prefetch_related('assignments')
        data = []
        for module in modules:
            for assignment in module.assignments.all():
                serializer = AssignmentSerializer(assignment)
                data.append(serializer.data)
        return Response(data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def participants(self, request, pk=None):
        course = self.get_object()
        enrollments = course.enrollments.select_related('user__profile')
        data = []
        for enrollment in enrollments:
            profile = enrollment.user.profile
            data.append({
                'user_id': enrollment.user.id,
                'email': enrollment.user.email,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'enrolled_at': enrollment.enroll_at,
            })
        return Response(data)


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_user=self.request.user)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def content(self, request, pk=None):
        module = self.get_object()
        contents = module.contents.all()
        serializer = ModuleContentSerializer(contents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def progress(self, request, pk=None):
        module = self.get_object()
        progress, created = UserProgress.objects.get_or_create(
            user=request.user, module=module,
            defaults={'status': 'in_progress'}
        )
        status_value = request.data.get('status', 'completed')
        if status_value == 'completed' and progress.status != 'completed':
            progress.status = 'completed'
            progress.completed_at = timezone.now()
            progress.save()
            profile = request.user.profile
            profile.total_points += module.point
            profile.save()
            # Update leaderboard
            course = module.course
            lb, _ = Leaderboard.objects.get_or_create(
                user=request.user, course=course,
                defaults={'points': 0}
            )
            lb.points += module.point
            lb.save()
        else:
            progress.status = status_value
            progress.save()
        return Response(UserProgressSerializer(progress).data)


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def submissions(self, request, pk=None):
        assignment = self.get_object()
        if request.method == 'POST':
            if Submission.objects.filter(assignment=assignment, user=request.user).exists():
                return Response({'detail': 'Already submitted'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = SubmissionSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(assignment=assignment, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        submissions = assignment.submissions.select_related('user__profile')
        if not request.user.groups.filter(name='Mentor').exists() and not request.user.is_staff:
            submissions = submissions.filter(user=request.user)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsMentorOrAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], permission_classes=[IsMentorOrAdmin])
    def grade(self, request, pk=None):
        submission = self.get_object()
        serializer = SubmissionGradeSerializer(submission, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(SubmissionSerializer(submission).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProgressViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProgress.objects.all()
    serializer_class = UserProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProgress.objects.filter(user=self.request.user)


class CourseEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CourseEnrollment.objects.all()
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CourseEnrollment.objects.filter(user=self.request.user).select_related('course')


class PaymentTransactionViewSet(viewsets.ModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PaymentTransaction.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [IsAdminOrReadOnly]


class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserBadge.objects.all()
    serializer_class = UserBadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user).select_related('badge')


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Leaderboard.objects.all()
    serializer_class = LeaderboardSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user
    profile = user.profile
    enrollments = CourseEnrollment.objects.filter(user=user).count()
    completed = UserProgress.objects.filter(user=user, status='completed').count()
    badges = UserBadge.objects.filter(user=user).select_related('badge')
    recent = UserProgress.objects.filter(user=user).order_by('-last_access_at')[:5]

    data = {
        'total_points': profile.total_points,
        'level': profile.level,
        'enrolled_courses': enrollments,
        'completed_modules': completed,
        'badges': UserBadgeSerializer(badges, many=True).data,
        'recent_activity': UserProgressSerializer(recent, many=True).data,
    }
    return Response(data)
